from types import SimpleNamespace

import numpy as np
import pytest

from amniotic.api import ApiAmniotic
from amniotic.recording import RecordingThemeStream
from amniotic.theme import ThemeStream


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
    response = await api.stream("sleep", request)

    assert response.background is not None
    response.background.func()
    assert created["stream"].closed is True
