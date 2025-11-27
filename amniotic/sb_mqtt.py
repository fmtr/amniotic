import asyncio

import homeassistant_api

from amniotic.client import ClientAmniotic
from amniotic.device import Amniotic
from fmtr.tools import Constants, env
from haco.constants import MQTT_HOST


async def main():
    HA_URL = env.get("HOME_ASSISTANT_URL")
    HA_TOKEN = env.get("HASSIO_TOKEN")

    client_ha = homeassistant_api.Client(HA_URL, HA_TOKEN)

    device = Amniotic(name=f"{Constants.DEVELOPMENT.capitalize()} Amniotic", client_ha=client_ha)

    client = ClientAmniotic(hostname=MQTT_HOST, device=device)
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
