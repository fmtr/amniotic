import asyncio

from amniotic.v2.client import ClientAmniotic
from amniotic.v2.device import Amniotic
from fmtr.tools import Constants
from haco.constants import MQTT_HOST


async def main():
    device = Amniotic(name=f"{Constants.DEVELOPMENT.capitalize()} Amniotic")
    client = ClientAmniotic(hostname=MQTT_HOST, device=device)
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
