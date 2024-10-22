import time

import av
import numpy as np

from fmtr.tools import logger


class Recording:
    CHUNK_SIZE = 1_024

    def __init__(self, path, volume):

        self.path = path
        self.volume = volume
        self.process = None
        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=44100)

        self.gen = self._gen()

    def _gen(self):

        while True:

            container = av.open(self.path)

            if len(container.streams.audio) == 0:
                raise ValueError('No audio stream')
            stream = next(iter(container.streams.audio))

            buffer = np.empty((1, 0), dtype=np.int16)

            for i, frame_orig in enumerate(container.decode(stream)):

                for frame_resamp in self.resampler.resample(frame_orig):
                    data_resamp = frame_resamp.to_ndarray()
                    data_resamp = data_resamp.mean(axis=0).astype(data_resamp.dtype).reshape(
                        data_resamp.shape)  # Downmix to mono
                    data_resamp = (data_resamp * self.volume).astype(data_resamp.dtype)  # Apply relative volume

                    buffer = np.hstack((buffer, data_resamp))  # Accumulate the array in the buffer

                    while buffer.shape[1] >= self.CHUNK_SIZE:
                        data = buffer[:, :self.CHUNK_SIZE]
                        buffer = buffer[:, self.CHUNK_SIZE:]  # Remove the yielded part from the buffer
                        logger.debug(
                            f'{self.__class__.__name__} Yielding {i=} {data_resamp.shape=} {data.shape=}, {buffer.shape=}, {self.path}')
                        yield data

            container.close()

    def __iter__(self):
        return self  # This returns the instance itself

    def __next__(self):
        """



        """
        return next(self.gen)


class Theme:

    def __init__(self, recordings):
        self.recordings = recordings

    def iter_chunks(self):

        while True:
            data_recs = [next(rec) for rec in self.recordings]
            data = np.vstack(data_recs)
            data = data.mean(axis=0).astype(data.dtype).reshape(1, -1)  # Mix recordings
            yield data

    def __iter__(self):
        output = av.open(file='.mp3', mode="w")
        bitrate = 128_000
        out_stream = output.add_stream(codec_name='mp3', rate=44100, channels=1, bit_rate=bitrate)
        gen_dec = self.iter_chunks()

        try:

            while True:

                for i, data in enumerate(gen_dec):
                    frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
                    frame.rate = 44100

                    for packet in out_stream.encode(frame):

                        pbytes = bytes(packet)

                        yield pbytes

                        if i > 100:
                            chunk_size = len(pbytes)  # Example chunk size (4 KB)
                            bytes_per_second = bitrate / 8
                            chunk_duration = chunk_size / bytes_per_second  # Duration of each chunk in seconds

                            time.sleep(chunk_duration)



        finally:
            print('Closing transcoder...')
            gen_dec.close()
            output.close()
