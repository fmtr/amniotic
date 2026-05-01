import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from amniotic.controls import EnableRecording, NumberVolume


class FakeClient:
    def __init__(self):
        self.topic = Path("amniotic")
        self.will = SimpleNamespace(topic="amniotic/status")
        self.published = []

    async def publish(self, topic, payload, retain=False):
        self.published.append(
            {
                "topic": str(topic),
                "payload": payload,
                "retain": retain,
            }
        )


class FakeThemes(list):
    def __init__(self, items):
        super().__init__(items)
        self.current = items[0]
        self.save_calls = 0

    @property
    def name(self):
        return {item.name: item for item in self}

    def save(self):
        self.save_calls += 1


class FakeInstances(list):
    def __init__(self, items):
        super().__init__(items)
        self.current = items[0]

    @property
    def name(self):
        return {item.name: item for item in self}


def build_device_for_control(control):
    client = FakeClient()
    instance = SimpleNamespace(name="Rain", volume=0.2, is_enabled=False)
    theme = SimpleNamespace(
        name="Sleep",
        url="https://stream.local/stream/sleep",
        instances=FakeInstances([instance]),
    )
    themes = FakeThemes([theme])
    bsn_theme_streamable = SimpleNamespace(calls=0)

    async def streamable_state():
        bsn_theme_streamable.calls += 1
        return True

    bsn_theme_streamable.state = streamable_state

    device = SimpleNamespace(
        name="Amniotic Development",
        name_san="amniotic-development",
        topic=client.topic / "amniotic-development",
        client=client,
        themes=themes,
        bsn_theme_streamable=bsn_theme_streamable,
    )

    control.set_parent(device)
    return device, client, theme, instance


@pytest.mark.asyncio
async def test_enable_recording_announce_message_is_published():
    control = EnableRecording()
    _, client, _, _ = build_device_for_control(control)

    await control.announce()

    assert len(client.published) == 1
    announce = client.published[0]
    assert announce["topic"] == "homeassistant/switch/amniotic-development-enable-recording/config"
    assert announce["retain"] is True

    payload = json.loads(announce["payload"])
    assert payload["platform"] == "switch"
    assert payload["name"] == "Enable Recording"
    assert payload["state_topic"] == "amniotic/amniotic-development/enable-recording/default/state"
    assert payload["command_topic"] == "amniotic/amniotic-development/enable-recording/default/command"
    assert payload["availability_topic"] == "amniotic/status"


@pytest.mark.asyncio
async def test_enable_recording_command_replay_publishes_state():
    control = EnableRecording()
    device, client, _, instance = build_device_for_control(control)

    await control.command(SimpleNamespace(payload=b"ON"))

    assert instance.is_enabled is True
    assert device.themes.save_calls == 1
    assert device.bsn_theme_streamable.calls == 1
    assert len(client.published) == 1
    assert client.published[0]["topic"].endswith("/enable-recording/default/state")
    assert client.published[0]["payload"] == "ON"
    assert client.published[0]["retain"] is True


@pytest.mark.asyncio
async def test_number_volume_command_and_state_replay_publishes_numeric_state():
    control = NumberVolume()
    device, client, _, instance = build_device_for_control(control)

    await control.command(SimpleNamespace(payload=b"37"))

    assert instance.volume == pytest.approx(0.37)
    assert device.themes.save_calls == 1
    assert len(client.published) == 1
    assert client.published[0]["topic"].endswith("/recording-volume/default/state")
    assert json.loads(client.published[0]["payload"]) == 37
    assert client.published[0]["retain"] is True
