from __future__ import annotations

import time

import anyio
import numpy as np
import typing
from functools import cached_property
from starlette.requests import Request

from amniotic.obs import logger
from amniotic.recording import LOG_THRESHOLD, RecordingThemeInstance, RecordingThemeStream
from corio import av, dt
from corio.constants import Constants
from corio.iterator_tools import IndexList
from corio.string_tools import sanitize
from haco.base import Base
from pydantic import Field

if typing.TYPE_CHECKING:
    from amniotic.device import Amniotic
    AmnioticRef = Amniotic
else:
    AmnioticRef = object


class IndexInstances(IndexList[RecordingThemeInstance]):

    def model_dump(self):
        return [item.model_dump() for item in self]

class ThemeDefinition(Base):
    """

    Run-time only. A ephemeral mix defined by the user.

    ThemeDefinition: What recordings are involved, volumes. User defines these via the UI, then selects a media player entity to stream from it.
    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.

    When a user selects a media player for this theme, then clicks play, HA tells the player to play URL /theme/name.
     - On the API side, the ThemeDefinition with ID "name" is selected, and a new ThemeStream initialized.

    When a user modifies a themeDefinition, like change recording volume, all live ThemeStreams are updated.

    Every ThemeDefinition needs an inited RecordingStream for each recording. That way we can have per-theme, per-recording state (volume, playing, etc).
    Not really. Cos each connection needs its own Stream.


    recording (immutable, one per-path) -> recording_instance (mutable, contains addition vol, is_enabled, etc) -> recording_stream (one per-connection)


    # Persistence

    - Have this class and RecordingInstance inherit from Base, and get model_dump method.
    - Subclass IndexList for Theme to Implement a save method that writes model_dump to disk.
    - Add a load classmethod(amniotic) to that class that loads from disk.
    - Saving will need to be manual, but there are limited places where it is needed, namely things like volume control command method.



    - Start out with an empty instances list, as instances can be created on the fly by the SelectRecording control

    """

    amniotic: AmnioticRef = Field(exclude=True, repr=False)
    instances: IndexInstances | list[RecordingThemeInstance] = Field(default_factory=list)
    name: str

    def model_post_init(self, __context):
        if type(self.instances) is list:
            self.instances = IndexInstances(self.instances)

        if not self.instances:
            meta = self.amniotic.metas.current
            if not meta:
                return
            instance = RecordingThemeInstance(device=self.amniotic, path=meta.path_str)
            self.instances.append(instance)
            self.instances.current = instance



    @cached_property
    def url(self) -> str:
        from amniotic.settings import settings
        return f'{settings.stream_url}/stream/{self.id}'

    @cached_property
    def id(self):
        return sanitize(self.name)

    @classmethod
    def from_data(cls, amniotic: 'Amniotic', data: dict):
        data_instances = data.pop('instances', [])

        instances = IndexInstances()
        for kwargs in data_instances:
            instance = RecordingThemeInstance(device=amniotic, **kwargs)
            if not instance.meta:
                logger.warning(f'Recording no longer exists "{instance.path}". Will be removed from Theme.')
                continue
            instances.append(instance)
            if not instances.current:
                instances.current = instance

        self = cls(amniotic=amniotic, instances=instances, **data)
        return self

    @property
    def is_enabled(self):
        return any(instance.is_enabled for instance in self.instances)

class ThemeStream:
    """




    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.
    When a user modifies a themeDefinition, like change recording volume, all live ThemeStreams are updated.

    """

    def __init__(self, theme_def: ThemeDefinition, request: Request):
        self.theme_def = theme_def
        self.request = request
        self.started_at = dt.now()
        self.started_at_str = self.started_at.strftime(Constants.DATETIME_FILENAME_FORMAT)
        self.recording_streams = IndexList[RecordingThemeStream]()
        self.iter_chunks_gen = None
        self.output = None
        self._is_closed = False
        logger.info(f'Initialized {repr(self)}')

    @cached_property
    def chunk_silence(self):
        from amniotic.recording import RecordingThemeStream
        data = np.zeros((1, RecordingThemeStream.CHUNK_SIZE), np.int16)
        return data

    @property
    def is_enabled(self):
        return self.theme_def.is_enabled

    def get_streams(self):
        names_map = self.recording_streams.name
        for instance in self.theme_def.instances:
            if not instance.is_enabled:
                continue
            stream = names_map.get(instance.name)
            if not stream:
                stream = RecordingThemeStream(instance=instance)
                self.recording_streams.append(stream)
            yield stream




    def iter_chunks(self):
        logger.debug(f'{repr(self)}: Starting to iterate chunks...')
        while True:
            streams = list(self.get_streams())
            data_recs = [next(stream) for stream in streams]
            if not data_recs:
                data_recs.append(self.chunk_silence)
            data = np.vstack(data_recs)
            data = data.mean(axis=0).astype(data.dtype).reshape(1, -1)  # Mix recordings
            yield data

    def __iter__(self):
        self.output = av.open(file='.mp3', mode="w")
        bitrate = 128_000
        out_stream = self.output.add_stream(codec_name='mp3', rate=44100, bit_rate=bitrate)
        self.iter_chunks_gen = self.iter_chunks()

        start_time = time.time()
        audio_time = 0.0  # total audio duration sent

        logger.debug(f'{repr(self)}: Starting transcoding loop...')

        try:
            while True:
                for i, data in enumerate(self.iter_chunks_gen):
                    if self._is_disconnected():
                        logger.info(f'{repr(self)}: Client disconnected. Stopping stream.')
                        return

                    vol_rms = round(float(np.sqrt((data.astype(np.float32) ** 2).mean())), 2)
                    frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
                    frame.rate = 44100

                    frame_duration = frame.samples / frame.rate
                    audio_time += frame_duration

                    size = 0
                    for packet in out_stream.encode(frame):
                        packet_bytes = bytes(packet)
                        size += len(packet_bytes)
                        yield packet_bytes

                    # Only sleep if we are ahead of real-time
                    now = time.time()
                    ahead = audio_time - (now - start_time)
                    if ahead > 0:
                        time.sleep(ahead)

                    if i % LOG_THRESHOLD == 0:
                        logger.info(f'{repr(self)}: Yielding chunk #{i} {vol_rms=} bytes={size}. Real-time delay {ahead:.5f}.')

        except Exception:
            logger.exception(f'{repr(self)}: Error in transcoding loop.')
            raise
        finally:
            self.close()

    def _is_disconnected(self) -> bool:
        try:
            return anyio.from_thread.run(self.request.is_disconnected)
        except RuntimeError:
            return False
        except Exception:
            logger.exception(f'{repr(self)}: Error checking client disconnection state.')
            return False

    def close(self):
        if self._is_closed:
            logger.debug(f'{repr(self)}: close() called, already closed.')
            return
        self._is_closed = True
        logger.info(f'{repr(self)}: Closing transcoder...')

        iter_chunks = self.iter_chunks_gen
        self.iter_chunks_gen = None
        if iter_chunks is not None:
            try:
                iter_chunks.close()
                logger.debug(f'{repr(self)}: Closed chunk mixer iterator.')
            except Exception:
                logger.exception(f'{repr(self)}: Error closing chunk mixer iterator.')
        else:
            logger.debug(f'{repr(self)}: No chunk mixer iterator to close.')

        logger.debug(f'{repr(self)}: Closing {len(self.recording_streams)} recording stream(s)...')
        for stream in list(self.recording_streams):
            try:
                stream.close()
            except Exception:
                logger.exception(f'{repr(self)}: Error closing recording stream {repr(stream)}.')
        self.recording_streams.clear()

        output = self.output
        self.output = None
        if output is not None:
            try:
                output.close()
                logger.debug(f'{repr(self)}: Closed output container.')
            except Exception:
                logger.exception(f'{repr(self)}: Error closing output container.')
        else:
            logger.debug(f'{repr(self)}: No output container to close.')

        logger.info(f'{repr(self)}: Transcoder closed.')

    def __repr__(self):
        return f'{self.__class__.__name__}(name={repr(self.theme_def.name)}, request={repr(self.request.client)}, started_at={self.started_at_str!r})'

class IndexThemes(IndexList[ThemeDefinition]):

    @classmethod
    def get_path_themes(cls):
        from amniotic.settings import settings
        return settings.path_themes

    @classmethod
    def load_data(cls):
        path_themes = cls.get_path_themes()

        if not path_themes.exists():
            logger.warning(f'No themes file found at "{path_themes}". No themes will be loaded.')
            return []

        with logger.span(f'Loading themes from "{path_themes}"'):
            data = path_themes.read_json()
            logger.info(f'Loaded {len(data)} themes.')

        return data

    @classmethod
    def load(cls, amniotic: 'Amniotic'):
        data = cls.load_data()
        self = cls.from_data(amniotic, data)
        return self

    @classmethod
    def from_data(cls, amniotic: 'Amniotic', data: list[dict]):
        themes = [ThemeDefinition.from_data(amniotic=amniotic, data=datum) for datum in data]
        self = cls(themes)
        return self

    def save(self):
        path = self.get_path_themes()
        with logger.span(f'Saving {len(self)} themes to "{path}"'):
            data = [theme.model_dump() for theme in self]
            return path.write_json(data)
