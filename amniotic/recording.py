from __future__ import annotations

import ctypes
import gc
import sys
import threading
import time
import typing

import numpy as np

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
HEAP_TRIM_INTERVAL = 30
_heap_trim_lock = threading.Lock()
_heap_trim_last = 0.0
_libc = ctypes.CDLL(None) if sys.platform.startswith('linux') else None


def trim_native_heap():
    """Periodically return released PyAV/NumPy allocations to the OS on Linux."""
    global _heap_trim_last

    if _libc is None or not hasattr(_libc, 'malloc_trim'):
        return

    now = time.monotonic()
    if now - _heap_trim_last < HEAP_TRIM_INTERVAL:
        return

    with _heap_trim_lock:
        now = time.monotonic()
        if now - _heap_trim_last < HEAP_TRIM_INTERVAL:
            return
        gc.collect()
        _libc.malloc_trim(0)
        _heap_trim_last = now


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
    SAMPLE_RATE = 44_100

    def __init__(self, instance: RecordingThemeInstance):
        self.instance = instance
        self.started_at = dt.now()
        self.started_at_str = self.started_at.strftime(Constants.DATETIME_FILENAME_FORMAT)
        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=self.SAMPLE_RATE)
        self.chunks = self.iter_chunks()

        self.container = None
        self.stream = None
        self._is_closed = False
        logger.info(f'Initialized {repr(self)} for path="{self.instance.path}"')

    @property
    def name(self):
        return self.instance.name

    def iter_samples(self):
        while True:
            self.container = av.open(self.instance.meta.path)

            try:
                if len(self.container.streams.audio) == 0:
                    raise ValueError(f'{repr(self)}. File has no audio stream.')
                self.stream = next(iter(self.container.streams.audio))

                with logger.span(f'Started transcoding: {repr(self)}'):
                    logger.info(self.description)

                for frame_orig in self.container.decode(self.stream):
                    data_orig = frame_orig.to_ndarray()
                    source_dtype = data_orig.dtype
                    if data_orig.shape[0] > 1:
                        data_orig = data_orig.mean(axis=0, dtype=np.float32).reshape(1, -1)
                    else:
                        data_orig = data_orig.reshape(1, -1)

                    if np.issubdtype(source_dtype, np.floating):
                        data_orig = data_orig.astype(np.float32, copy=False)
                        data_orig *= self.instance.volume
                        np.clip(data_orig, -1.0, 1.0, out=data_orig)
                        data_orig = (data_orig * np.iinfo(np.int16).max).astype(np.int16)
                    else:
                        np.multiply(data_orig, self.instance.volume, out=data_orig, casting='unsafe')
                        np.clip(data_orig, np.iinfo(np.int16).min, np.iinfo(np.int16).max, out=data_orig)
                        data_orig = data_orig.astype(np.int16, copy=False)
                    frame_mono = av.AudioFrame.from_ndarray(data_orig, format='s16', layout='mono')
                    frame_mono.rate = self.stream.codec_context.rate
                    for frame_resamp in self.resampler.resample(frame_mono):
                        yield frame_resamp.to_ndarray().reshape(-1)
            finally:
                self._close_container()

    def iter_chunks(self):
        sample_blocks = self.iter_samples()
        buffer = np.empty(self.CHUNK_SIZE, dtype=np.int16)
        buffered = 0
        i = 0
        try:
            for block in sample_blocks:
                offset = 0
                while offset < block.size:
                    copied = min(self.CHUNK_SIZE - buffered, block.size - offset)
                    buffer[buffered:buffered + copied] = block[offset:offset + copied]
                    buffered += copied
                    offset += copied

                    if buffered < self.CHUNK_SIZE:
                        continue

                    data = buffer.copy().reshape(1, -1)
                    buffered = 0
                    yield data

                    if i % LOG_THRESHOLD == 0:
                        trim_native_heap()
                        vol_rms = round(float(np.sqrt((data.astype(np.float32) ** 2).mean())), 2)
                        logger.info(f'{repr(self)}: Yielding chunk #{i} {data.shape=}, {vol_rms=}')
                    i += 1
        finally:
            sample_blocks.close()

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
