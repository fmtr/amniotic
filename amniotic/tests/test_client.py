import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import pytest

from amniotic.client import ClientAmniotic
from haco.client import ClientHaco


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class CaptureClient(ClientAmniotic):
    def __init__(self, device, *args, **kwargs):
        self.device = device
        self.kwargs = kwargs


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_json(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.mark.asyncio
async def test_client_start_runs_mqtt_and_api_launch(monkeypatch):
    events = []

    async def fake_super_start(self):
        events.append("mqtt_start")

    async def fake_launch_async(client):
        events.append(("api_launch", client))

    monkeypatch.setattr(ClientHaco, "start", fake_super_start)
    monkeypatch.setattr(
        ClientAmniotic,
        "API_CLASS",
        type("DummyApi", (), {"launch_async": staticmethod(fake_launch_async)}),
    )

    client = object.__new__(ClientAmniotic)
    client._client = SimpleNamespace(username="tester")
    client._hostname = "mqtt.local"
    client._port = 1883

    await ClientAmniotic.start(client)

    assert "mqtt_start" in events
    assert ("api_launch", client) in events


def test_from_supervisor_uses_mqtt_service_payload(monkeypatch):
    fake_settings = SimpleNamespace(
        ha_supervisor_api="http://supervisor.local",
        token="token123",
    )
    fake_settings_mod = ModuleType("amniotic.settings")
    fake_settings_mod.settings = fake_settings
    monkeypatch.setitem(sys.modules, "amniotic.settings", fake_settings_mod)

    captured = {}

    def fake_get(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return DummyResponse(_fixture_json("supervisor_services_mqtt.json"))

    monkeypatch.setattr("amniotic.client.http.client.get", fake_get)

    device = object()
    client = CaptureClient.from_supervisor(device=device)

    assert captured["url"] == "http://supervisor.local/services/mqtt"
    assert captured["headers"]["Authorization"] == "Bearer token123"
    assert client.device is device
    assert client.kwargs["hostname"] == "mqtt.service"
    assert client.kwargs["port"] == 1883
    assert client.kwargs["username"] == "addons"
    assert client.kwargs["password"] == "example-password"


def test_from_supervisor_raises_when_mqtt_service_is_missing(monkeypatch):
    fake_settings = SimpleNamespace(
        ha_supervisor_api="http://supervisor.local",
        token="token123",
    )
    fake_settings_mod = ModuleType("amniotic.settings")
    fake_settings_mod.settings = fake_settings
    monkeypatch.setitem(sys.modules, "amniotic.settings", fake_settings_mod)

    monkeypatch.setattr(
        "amniotic.client.http.client.get",
        lambda *args, **kwargs: DummyResponse({"data": {}}),
    )

    with pytest.raises(RuntimeError, match="MQTT service not found"):
        CaptureClient.from_supervisor(device=object())
