from __future__ import annotations

import time
import typing
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np

from amniotic.obs import logger
from amniotic.recording import LOG_THRESHOLD, RecordingThemeInstance
from fmtr.tools import av
from fmtr.tools.iterator_tools import IndexList
from fmtr.tools.string_tools import sanitize
from haco.base import Base

if typing.TYPE_CHECKING:
    from amniotic.device import Amniotic


class IndexInstances(IndexList[RecordingThemeInstance]):

    def model_dump(self):
        return [item.model_dump() for item in self]

@dataclass(kw_only=True)
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

    amniotic: Amniotic = field(metadata=dict(exclude=True))
    instances: IndexInstances | list[RecordingThemeInstance] = field(default_factory=list)
    name: str

    def __post_init__(self):
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


    def get_stream(self):
        theme = ThemeStream(self)
        return theme

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



class ThemeStream:
    """




    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.
    When a user modifies a themeDefinition, like change recording volume, all live ThemeStreams are updated.

    """

    def __init__(self, theme_def: ThemeDefinition):
        self.theme_def = theme_def
        self.recording_streams = [instance.get_stream() for instance in theme_def.instances]

    @cached_property
    def chunk_silence(self):
        from amniotic.recording import RecordingThemeStream
        data = np.zeros((1, RecordingThemeStream.CHUNK_SIZE), np.int16)
        return data

    @property
    def is_enabled(self):
        return any(stream.instance.is_enabled for stream in self.recording_streams)

    def iter_chunks(self):

        while True:
            data_recs = [next(stream) for stream in self.recording_streams if stream.instance.is_enabled]
            if not data_recs:
                data_recs.append(self.chunk_silence)
            data = np.vstack(data_recs)
            data = data.mean(axis=0).astype(data.dtype).reshape(1, -1)  # Mix recordings
            yield data

    def __iter__(self):
        output = av.open(file='.mp3', mode="w")
        bitrate = 128_000
        out_stream = output.add_stream(codec_name='mp3', rate=44100, bit_rate=bitrate)
        iter_chunks = self.iter_chunks()

        start_time = time.time()
        audio_time = 0.0  # total audio duration sent

        try:
            while True:
                for i, data in enumerate(iter_chunks):
                    frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
                    frame.rate = 44100

                    frame_duration = frame.samples / frame.rate
                    audio_time += frame_duration

                    for packet in out_stream.encode(frame):
                        packet_bytes = bytes(packet)
                        yield packet_bytes

                    # Only sleep if we are ahead of real-time
                    now = time.time()
                    ahead = audio_time - (now - start_time)
                    if ahead > 0:
                        time.sleep(ahead)

                    if i % LOG_THRESHOLD == 0:
                        logger.debug(f'Waiting {ahead:.5f} seconds to maintain real-time pacing {audio_time=}...')


        finally:
            logger.info('Closing transcoder...')
            iter_chunks.close()
            output.close()


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
            data = path_themes.read_yaml()
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
