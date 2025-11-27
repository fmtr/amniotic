from homeassistant_api import Client

from fmtr.tools import env

# These match how HA add-ons expose configuration
HA_URL = env.get("HOME_ASSISTANT_URL")
HA_TOKEN = env.get("HASSIO_TOKEN")

if not HA_TOKEN:
    raise SystemExit("Missing HASSIO_TOKEN or SUPERVISOR_TOKEN")

client = Client(HA_URL, HA_TOKEN)


def list_media_players():
    """Returns a list of dicts for all media_player entities"""
    states = client.get_states()  # latest library returns list of dicts
    return [s for s in states if s.entity_id.startswith("media_player.")]


def play_stream(entity_id, url):
    media_player = client.get_domain("media_player")
    media_player.play_media(
        entity_id=entity_id,
        media_content_id=url,
        media_content_type="music",
    )


# --- Example usage ---
if __name__ == "__main__":
    print("Available media players:")
    for p in list_media_players():
        print(f"{p.entity_id} → {p.state}")

    play_stream("media_player.ws_lan", "https://amniotic.ws.gex.fmtr.dev/stream/default-a")
