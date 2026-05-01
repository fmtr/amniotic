import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

from amniotic.device import Amniotic, MediaState


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_json(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def test_media_state_from_state_parses_realistic_home_assistant_payload():
    payload = {
        "entity_id": "media_player.living_room_speaker",
        "state": "idle",
        "attributes": {
            "friendly_name": "Living Room Speaker",
            "supported_features": 152461,
            "volume_level": 0.42,
        },
        "last_changed": "2026-04-30T10:00:00+00:00",
    }

    state = MediaState.from_state(payload)

    assert state.entity_id == "media_player.living_room_speaker"
    assert state.state == "idle"
    assert state.friendly_name == "Living Room Speaker"
    assert state.supported_features == 152461


def test_media_state_falls_back_to_entity_id_when_friendly_name_missing():
    payload = {
        "entity_id": "media_player.office",
        "state": "playing",
        "attributes": {},
    }

    state = MediaState.from_state(payload)

    assert state.friendly_name == "media_player.office"


def test_get_media_players_replays_states_payload(monkeypatch):
    fake_settings = SimpleNamespace(ha_core_api="http://ha.local/api", token="token123")
    fake_settings_mod = ModuleType("amniotic.settings")
    fake_settings_mod.settings = fake_settings
    monkeypatch.setitem(sys.modules, "amniotic.settings", fake_settings_mod)

    payload = _fixture_json("ha_states.json")

    class DummyResponse:
        def json(self):
            return payload

        def raise_for_status(self):
            return None

    captured = {}

    def fake_get(url, headers):
        captured["url"] = url
        captured["headers"] = headers
        return DummyResponse()

    monkeypatch.setattr("amniotic.device.client_ha.get", fake_get)

    players = Amniotic.get_media_players(object())

    assert captured["url"] == "http://ha.local/api/states"
    assert captured["headers"]["Authorization"] == "Bearer token123"
    assert [player.entity_id for player in players] == [
        "media_player.living_room",
        "media_player.office",
    ]
