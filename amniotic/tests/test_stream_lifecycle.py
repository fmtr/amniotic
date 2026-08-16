from types import SimpleNamespace

import numpy as np
import pytest

from amniotic.api import ApiAmniotic, Stream
from amniotic import recording
from amniotic.recording import RecordingThemeStream
from amniotic.theme import ThemeStream


def test_native_heap_trim_is_rate_limited(monkeypatch):
    class FakeLibc:
        def __init__(self):
            self.calls = 0

        def malloc_trim(self, _padding):
            self.calls += 1

    libc = FakeLibc()
    times = iter([100.0, 100.0, 101.0, 131.0, 131.0])
    monkeypatch.setattr(recording, "_libc", libc)
    monkeypatch.setattr(recording, "_heap_trim_last", 0.0)
    monkeypatch.setattr(recording.time, "monotonic", lambda: next(times))

    recording.trim_native_heap()
    recording.trim_native_heap()
    recording.trim_native_heap()

    assert libc.calls == 2


def test_recording_stream_chunks_sample_blocks_without_losing_samples(monkeypatch):
    stream = RecordingThemeStream.__new__(RecordingThemeStream)
    stream.CHUNK_SIZE = 4
    stream.instance = SimpleNamespace(name="demo")
    stream.started_at_str = "test"

    def sample_blocks():
        yield np.array([0, 1, 2], dtype=np.int16)
        yield np.array([3, 4, 5, 6, 7, 8], dtype=np.int16)

    monkeypatch.setattr(stream, "iter_samples", sample_blocks)
    monkeypatch.setattr("amniotic.recording.LOG_THRESHOLD", 10_000)

    chunks = list(stream.iter_chunks())

    assert [chunk.tolist() for chunk in chunks] == [
        [[0, 1, 2, 3]],
        [[4, 5, 6, 7]],
    ]


def test_recording_stream_close_releases_container(monkeypatch):
    class FakeInputFrame:
        def to_ndarray(self):
            return np.ones((1, RecordingThemeStream.CHUNK_SIZE), dtype=np.int16)

    class FakeResampledFrame:
        def to_ndarray(self):
            return np.ones((1, RecordingThemeStream.CHUNK_SIZE), dtype=np.int16)

    class FakeResampler:
        def resample(self, _frame):
            return [FakeResampledFrame()]

    class FakeContainer:
        def __init__(self):
            self.closed = False
            codec_context = SimpleNamespace(
                codec=SimpleNamespace(long_name="fake-codec"),
                layout=SimpleNamespace(name="mono"),
                rate=44100,
            )
            self.streams = SimpleNamespace(audio=[SimpleNamespace(codec_context=codec_context)])
            self.format = SimpleNamespace(long_name="fake-format")

        def decode(self, _stream):
            while True:
                yield FakeInputFrame()

        def close(self):
            self.closed = True

    container = FakeContainer()

    monkeypatch.setattr("amniotic.recording.av.open", lambda *_args, **_kwargs: container)
    monkeypatch.setattr("amniotic.recording.av.AudioResampler", lambda **_kwargs: FakeResampler())

    instance = SimpleNamespace(
        path="file.mp3",
        volume=1.0,
        meta=SimpleNamespace(path="file.mp3"),
        name="demo",
    )
    stream = RecordingThemeStream(instance=instance)

    next(stream)
    stream.close()

    assert container.closed is True
    assert stream.container is None
    assert stream.stream is None
    assert stream.chunks is None


def test_theme_stream_mixes_without_attenuating_enabled_recordings(monkeypatch):
    theme_def = SimpleNamespace(name="Sleep", is_enabled=True, instances=[])
    request = SimpleNamespace(client=("127.0.0.1", 1234), is_disconnected=lambda: False)
    stream = ThemeStream(theme_def=theme_def, request=request)
    chunks = [
        np.array([[10_000, 20_000]], dtype=np.int16),
        np.array([[10_000, 20_000]], dtype=np.int16),
    ]
    monkeypatch.setattr(stream, "get_streams", lambda: (iter(chunk) for chunk in chunks))

    mixed = next(stream.iter_chunks())

    assert mixed.tolist() == [[20_000, np.iinfo(np.int16).max]]


def test_theme_stream_generator_close_releases_output_and_children(monkeypatch):
    class FakeOutputStream:
        def encode(self, _frame):
            return [b"chunk"]

    class FakeOutput:
        def __init__(self):
            self.closed = False

        def add_stream(self, **_kwargs):
            return FakeOutputStream()

        def close(self):
            self.closed = True

    class FakeRecordingStream:
        def __init__(self):
            self.closed = False

        def __next__(self):
            return np.zeros((1, RecordingThemeStream.CHUNK_SIZE), dtype=np.int16)

        def close(self):
            self.closed = True

    outputs = []

    def fake_open(*_args, **_kwargs):
        output = FakeOutput()
        outputs.append(output)
        return output

    monkeypatch.setattr("amniotic.theme.av.open", fake_open)

    theme_def = SimpleNamespace(name="Sleep", is_enabled=True, instances=[])
    request = SimpleNamespace(client=("127.0.0.1", 1234), is_disconnected=lambda: False)
    stream = ThemeStream(theme_def=theme_def, request=request)

    rec_stream = FakeRecordingStream()
    stream.recording_streams.append(rec_stream)
    monkeypatch.setattr(stream, "get_streams", lambda: iter([rec_stream]))

    gen = iter(stream)
    next(gen)
    gen.close()

    assert rec_stream.closed is True
    assert outputs and outputs[0].closed is True
    assert stream.output is None


@pytest.mark.asyncio
async def test_api_stream_response_registers_background_cleanup(monkeypatch):
    theme_def = SimpleNamespace(name="Sleep", id="sleep")
    device = SimpleNamespace(themes=SimpleNamespace(id={"sleep": theme_def}))
    client = SimpleNamespace(device=device)
    api = ApiAmniotic(client=client)

    created = {}

    class FakeThemeStream:
        def __init__(self, theme_def, request):
            created["stream"] = self
            self.theme_def = theme_def
            self.request = request
            self.closed = False
            self.is_enabled = True

        def __iter__(self):
            return self

        def __next__(self):
            raise StopIteration

        def close(self):
            self.closed = True

    monkeypatch.setattr("amniotic.api.ThemeStream", FakeThemeStream)

    request = SimpleNamespace(client=("127.0.0.1", 1234))
    response = await api.endpoints.cls[Stream].run("sleep", request)

    assert response.background is not None
    response.background.func()
    assert created["stream"].closed is True
