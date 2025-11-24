import asyncio
import logging

from amniotic.paths import paths
from amniotic.v2.api import ApiAmniotic
from amniotic.v2.recording import RecordingDefinition
from fmtr.tools import Constants
from haco.client import ClientHaco
from haco.constants import MQTT_HOST
from haco.device import Device
from haco.obs import logger
from haco.pulldown import Select

handler = logger.LogfireLoggingHandler()
logging.basicConfig(handlers=[handler], level=logging.DEBUG)


class SelectRecording(Select):

    def command(self, value):
        value


class Amniotic(Device):
    DEFINITIONS = [RecordingDefinition(paths.example_700KB), RecordingDefinition(paths.gambling)]  # All those on disk.


class ClientAmniotic(ClientHaco):
    """
    Take an extra API argument, and gather with super.start
    """

    API_CLASS = ApiAmniotic

    def __init__(self, device: Amniotic, *args, **kwargs):
        super().__init__(device=device, *args, **kwargs)

    async def start(self):
        await asyncio.gather(
            super().start(),
            self.API_CLASS.launch_async(self)
        )


async def main():
    sel1 = SelectRecording(name="Recordings", options=[str(defin.path) for defin in Amniotic.DEFINITIONS])
    device = Amniotic(name=f"{Constants.DEVELOPMENT} Amniotic", controls=[sel1])

    client = ClientAmniotic(hostname=MQTT_HOST, device=device, logger=logging.getLogger(__name__))
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
