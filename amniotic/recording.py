import numpy as np

from amniotic.obs import logger
from fmtr.tools import av

LOG_THRESHOLD = 500


class RecordingMetadata:
    """

    Represents file, metadata, etc. The non-state stuff, on disk. One per file. Immutable

    """

    def __init__(self, path):
        self.path = path

    def get_instance(self):
        return RecordingThemeInstance(self)

    @property
    def name(self):
        return self.path.stem


class RecordingThemeInstance:
    """

    Wraps the metadata, but with some extra state, to represent how that recording is set up within a given theme.
    Every theme gets one of these for each recording.

    ThemeDef.recording_current=RecordingThemeInstance
    This needs methods like setting volume that apply to all children streams.

    """

    def __init__(self, meta: RecordingMetadata):
        self.meta = meta
        # self.streams: list['RecordingThemeStream'] = []
        self.volume = 0.5
        self.is_enabled = False

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

        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=44100)

        self.gen = self._gen()

    def _gen(self):

        while True:

            container = av.open(self.instance.meta.path)

            if len(container.streams.audio) == 0:
                raise ValueError('No audio stream')
            stream = next(iter(container.streams.audio))

            buffer = np.empty((1, 0), dtype=np.int16)

            i = 0
            for frame_orig in container.decode(stream):

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
                            vol_mean = round(abs(data).mean())
                            logger.info(f'{self.__class__.__name__} Yielding chunk #{i} {data_resamp.shape=} {data.shape=}, {buffer.shape=}, {vol_mean=} {self.instance.meta.path=}')
                        i += 1

            container.close()

    def __iter__(self):
        return self  # This returns the instance itself

    def __next__(self):
        """



        """
        return next(self.gen)


