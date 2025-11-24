import time

import numpy as np

from amniotic.obs import logger
from amniotic.paths import paths
from fmtr.tools import av

LOG_THRESHOLD = 500

class RecordingDefinition:

    def __init__(self, path):
        self.path = path

    def get_stream(self):
        return RecordingStream(self)


class RecordingStream:
    """

    Should be split into two:

    RecordingDefinition: Represents file, metadata, etc. The non-state stuff, on disk.
    RecordingStream: An open stream on that file, ready to decode. Many instances, one-per-client.


    """
    CHUNK_SIZE = 1_024


    def __init__(self, definition: RecordingDefinition):

        self.definition = definition
        self.volume = 0.5
        self.resampler = av.AudioResampler(format='s16', layout='mono', rate=44100)

        self.gen = self._gen()

    def _gen(self):

        while True:

            container = av.open(self.definition.path)

            if len(container.streams.audio) == 0:
                raise ValueError('No audio stream')
            stream = next(iter(container.streams.audio))

            buffer = np.empty((1, 0), dtype=np.int16)

            i = 0
            for frame_orig in container.decode(stream):

                for frame_resamp in self.resampler.resample(frame_orig):
                    data_resamp = frame_resamp.to_ndarray()
                    data_resamp = data_resamp.mean(axis=0).astype(data_resamp.dtype).reshape(
                        data_resamp.shape)  # Downmix to mono
                    data_resamp = (data_resamp * self.volume).astype(data_resamp.dtype)  # Apply relative volume

                    buffer = np.hstack((buffer, data_resamp))  # Accumulate the array in the buffer

                    while buffer.shape[1] >= self.CHUNK_SIZE:
                        data = buffer[:, :self.CHUNK_SIZE]
                        buffer = buffer[:, self.CHUNK_SIZE:]  # Remove the yielded part from the buffer

                        yield data

                        if i % LOG_THRESHOLD == 0:
                            logger.debug(f'{self.__class__.__name__} Yielding {i=} {data_resamp.shape=} {data.shape=}, {buffer.shape=}, {self.definition.path=}')
                        i += 1

            container.close()

    def __iter__(self):
        return self  # This returns the instance itself

    def __next__(self):
        """



        """
        return next(self.gen)


class ThemeDefinition:
    """

    Run-time only. A ephemeral mix defined by the user.

    ThemeDefinition: What recordings are involved, volumes. User defines these via the UI, then selects a media player entity to stream from it.
    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.

    When a user selectes a media player for this theme, then clicks play, HA tells the player to play URL /theme/name.
     - On the API side, the ThemeDefinition with ID "name" is selected, and a new ThemeStream initialized.

    When a user modifies a themeDefinition, like change recording volume, all live ThemeStreams are updated.

    """

    DEFINITIONS = [RecordingDefinition(paths.example_700KB), RecordingDefinition(paths.gambling)]  # All those on disk.

    def __init__(self, name):
        self.name = name

        self.definitions = []
        self.streams = []

    def get_stream(self):
        theme = ThemeStream(self)
        self.streams.append(theme)
        return theme

    def enable(self, definition: RecordingDefinition):
        self.definitions.append(definition)
        for stream in self.streams:
            stream.enable(definition)

    def disable(self, definition: RecordingDefinition):
        self.definitions.remove(definition)
        for stream in self.streams:
            stream.disable(definition)


class ThemeStream:
    """

    Run-time only. A ephemeral mix defined by the user.

    ThemeDefinition: What recordings are involved, volumes. User defines these via the UI, then selects a media player entity to stream from it.
    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.

    When a user selectes a media player for this theme, then clicks play, HA tells the player to play URL /theme/name.
     - On the API side, the ThemeDefinition with ID "name" is selected, and a new ThemeStream initialized.

    When a user modifies a themeDefinition, like change recording volume, all live ThemeStreams are updated.

    """

    def enable(self, definition: RecordingDefinition):
        self.streams.append(definition.get_stream())
        self

    def disable(self, definition: RecordingDefinition):
        self.streams = [stream for stream in self.streams if stream.definition is not definition]

    def __init__(self, definition: ThemeDefinition):
        self.definition = definition
        self.streams = []
        for definition in self.definition.definitions:
            self.enable(definition)

    def iter_chunks(self):

        while True:
            data_recs = [next(rec) for rec in self.streams]
            data = np.vstack(data_recs)
            data = data.mean(axis=0).astype(data.dtype).reshape(1, -1)  # Mix recordings
            yield data

    def __iter__(self):
        output = av.open(file='.mp3', mode="w")
        bitrate = 128_000
        out_stream = output.add_stream(codec_name='mp3', rate=44100, bit_rate=bitrate)
        gen_dec = self.iter_chunks()

        start_time = time.time()
        audio_time = 0.0  # total audio duration sent

        try:
            while True:
                for i, data in enumerate(gen_dec):
                    frame = av.AudioFrame.from_ndarray(data, format='s16', layout='mono')
                    frame.rate = 44100

                    frame_duration = frame.samples / frame.rate
                    audio_time += frame_duration

                    for packet in out_stream.encode(frame):
                        pbytes = bytes(packet)
                        yield pbytes

                    # Only sleep if we are ahead of real-time
                    now = time.time()
                    ahead = audio_time - (now - start_time)
                    if ahead > 0:
                        time.sleep(ahead)

                    if i % LOG_THRESHOLD == 0:
                        logger.debug(f'Waiting {ahead:.5f} seconds to maintain real-time pacing {audio_time=} {abs(data).mean()=}...')


        finally:
            print('Closing transcoder...')
            gen_dec.close()
            output.close()
