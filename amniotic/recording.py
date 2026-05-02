from __future__ import annotations

import numpy as np
import typing

from amniotic.obs import logger
from corio import av, dt
from corio.constants import Constants
from haco.base import Base
from pydantic import Field

if typing.TYPE_CHECKING:
    from amniotic.device import Amniotic
    AmnioticRef = Amniotic
else:
    AmnioticRef = object

LOG_THRESHOLD = 500


class RecordingMetadata:
    """

    Represents file, metadata, etc. The non-state stuff, on disk. One per file. Immutable

    """

    def __init__(self, path):
        self.path = path

    def get_instance(self, device: 'Amniotic'):
        return RecordingThemeInstance(device=device, path=self.path_str)

    @property
    def name(self):
        return self.path.stem

    @property
    def path_str(self):
        return str(self.path)


class RecordingThemeInstance(Base):
    """

    Wraps the metadata, but with some extra state, to represent how that recording is set up within a given theme.
    Every theme gets one of these for each recording.

    ThemeDef.recording_current=RecordingThemeInstance
    This needs methods like setting volume that apply to all children streams.


    To handle removed recording fields on disk, this class needs to either raise on init if missing - or

    There are two ways this object can become invalid:

    - If it gets access (e.g. by a stream) when it's just been deleted from disk. Even then, deleting would presumably not be possible while streaming?
    - Amniotic notices it's been deleted (scheduled polling)    -

    """

    device: AmnioticRef = Field(exclude=True, repr=False)

    path: str
    volume: float = 0.2
    is_enabled: bool = False

    @property
    def meta(self):
        return self.device.metas.path_str.get(self.path)


    def get_stream(self):
        return RecordingThemeStream(self)

    @property
    def name(self):
        return self.meta.name


class RecordingThemeStream:
    """

    Representation of the audio stream, per-theme, per-connection. So multiple mediaplays can play the one theme, but each needs its own stream.

    """
    CHUNK_SIZE = 1_024

    def __init__(self, instance: RecordingThemeInstance):
        self.instance = instance
        self.started_at = dt.now()
        self.started_at_str = self.started_at.strftime(Constants.DATETIME_FILENAME_FORMAT)
        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=44100)
        self.chunks = self.iter_chunks()

        self.container = None
        self.stream = None
        self._is_closed = False
        logger.info(f'Initialized {repr(self)} for path="{self.instance.path}"')

    @property
    def name(self):
        return self.instance.name

    def iter_chunks(self):

        while True:

            self.container = av.open(self.instance.meta.path)

            try:
                if len(self.container.streams.audio) == 0:
                    raise ValueError(f'{repr(self)}. File has no audio stream.')
                self.stream = next(iter(self.container.streams.audio))

                with logger.span(f'Started transcoding: {repr(self)}'):
                    logger.info(self.description)

                buffer = np.empty((1, 0), dtype=np.int16)

                i = 0
                for frame_orig in self.container.decode(self.stream):

                    for frame_resamp in self.resampler.resample(frame_orig):
                        data_resamp = frame_resamp.to_ndarray()
                        data_resamp = data_resamp.mean(axis=0).astype(data_resamp.dtype).reshape(data_resamp.shape)  # Downmix to mono
                        data_resamp = (data_resamp * self.instance.volume).astype(data_resamp.dtype)  # Apply relative volume

                        buffer = np.hstack((buffer, data_resamp))  # Accumulate the array in the buffer

                        while buffer.shape[1] >= self.CHUNK_SIZE:
                            data = buffer[:, :self.CHUNK_SIZE]
                            buffer = buffer[:, self.CHUNK_SIZE:]  # Remove the yielded part from the buffer

                            yield data

                            if i % LOG_THRESHOLD == 0:
                                vol_rms = round(float(np.sqrt((data.astype(np.float32) ** 2).mean())), 2)
                                logger.info(f'{repr(self)}: Yielding chunk #{i} {data_resamp.shape=} {data.shape=}, {buffer.shape=}, {vol_rms=}')
                            i += 1
            finally:
                self._close_container()

    def __iter__(self):
        return self  # This returns the instance itself

    def __next__(self):
        """



        """
        if self.chunks is None:
            raise StopIteration
        return next(self.chunks)

    def _close_container(self):
        container = self.container
        self.container = None
        self.stream = None
        if container is None:
            return
        try:
            container.close()
        except Exception:
            logger.exception(f'{repr(self)}: Error closing input container.')

    def close(self):
        if self._is_closed:
            logger.debug(f'{repr(self)}: close() called, already closed.')
            return
        self._is_closed = True
        logger.info(f'{repr(self)}: Closing recording stream...')

        chunks = self.chunks
        self.chunks = None
        if chunks is not None:
            try:
                chunks.close()
                logger.debug(f'{repr(self)}: Closed chunk iterator.')
            except Exception:
                logger.exception(f'{repr(self)}: Error closing chunk iterator.')
        else:
            logger.debug(f'{repr(self)}: No chunk iterator to close.')

        self._close_container()
        logger.info(f'{repr(self)}: Recording stream closed.')

    @property
    def description(self):
        desc = f'Container: {self.container.format.long_name}. Codec: {self.stream.codec_context.codec.long_name}. Layout: {self.stream.codec_context.layout.name}. Rate: {self.stream.codec_context.rate}'
        return desc

    def __repr__(self):
        return f'{self.__class__.__name__}(name={repr(self.name)}, started_at={self.started_at_str!r})'
