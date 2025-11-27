import time
from functools import cached_property

import numpy as np

from amniotic.obs import logger
from amniotic.recording import LOG_THRESHOLD, RecordingThemeInstance
from fmtr.tools import av
from fmtr.tools.string_tools import sanitize


class ThemeDefinition:
    """

    Run-time only. A ephemeral mix defined by the user.

    ThemeDefinition: What recordings are involved, volumes. User defines these via the UI, then selects a media player entity to stream from it.
    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.

    When a user selectes a media player for this theme, then clicks play, HA tells the player to play URL /theme/name.
     - On the API side, the ThemeDefinition with ID "name" is selected, and a new ThemeStream initialized.

    When a user modifies a themeDefinition, like change recording volume, all live ThemeStreams are updated.

    Every ThemeDefinition needs an inited RecordingStream for each recording. That way we can have per-theme, per-recording state (volume, playing, etc).
    Not really. Cos each connection needs its own Stream.


    recording (immutable, one per-path) -> recording_instance (mutable, contains addition vol, is_enabled, etc) -> recording_stream (one per-connection)

    """

    def __init__(self, amniotic, name):
        self.amniotic = amniotic
        self.name = name

        self.instances: list[RecordingThemeInstance] = [meta.get_instance() for meta in self.amniotic.metas]
        self.instance_current = next(iter(self.instances))

        self.streams: list[ThemeStream] = []

    @cached_property
    def id(self):
        return sanitize(self.name)

    @cached_property
    def instance_lookup(self):
        return {instance.name: instance for instance in self.instances}

    @logger.instrument('Setting Theme "{self.name}" current recording instance to "{name}"...')
    def set_instance(self, name):
        instance = self.instance_lookup[name]
        self.instance_current = instance

    def get_stream(self):
        theme = ThemeStream(self)
        self.streams.append(theme)
        return theme


class ThemeStream:
    """

    Run-time only. A ephemeral mix defined by the user.

    ThemeDefinition: What recordings are involved, volumes. User defines these via the UI, then selects a media player entity to stream from it.
    ThemeStream: One instance per client/connection. Has a RecordingStream for each recording in the ThemeDefinition.

    When a user selectes a media player for this theme, then clicks play, HA tells the player to play URL /theme/name.
     - On the API side, the ThemeDefinition with ID "name" is selected, and a new ThemeStream initialized.

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

    def iter_chunks(self):

        while True:
            data_recs = [next(streams) for streams in self.recording_streams if streams.instance.is_enabled]
            if not data_recs:
                # logger.debug(f'Theme "{self.theme_def.name}" has no enabled recordings. Streaming silence...')
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
                        logger.debug(f'Waiting {ahead:.5f} seconds to maintain real-time pacing {audio_time=} {abs(data).mean()=}...')


        finally:
            logger.info('Closing transcoder...')
            iter_chunks.close()
            output.close()
