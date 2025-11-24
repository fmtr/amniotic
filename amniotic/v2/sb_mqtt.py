import asyncio
import logging
from dataclasses import dataclass
from functools import cached_property

from amniotic.paths import paths
from amniotic.v2.api import ApiAmniotic
from amniotic.v2.recording import RecordingDefinition
from fmtr.tools import Constants
from haco.button import Button
from haco.client import ClientHaco
from haco.constants import MQTT_HOST
from haco.device import Device
from haco.obs import logger
from haco.pulldown import Select

handler = logger.LogfireLoggingHandler()
logging.basicConfig(handlers=[handler], level=logging.DEBUG)


@dataclass(kw_only=True)
class SelectRecording(Select):

    def command(self, value):
        value


@dataclass(kw_only=True)
class ButtonChangeTheme(Button):

    async def command(self, value):
        self.device.select_recording.options = ['a', 'b', 'c']
        await self.device.select_recording.announce()
        value


@dataclass(kw_only=True)
class Amniotic(Device):
    DEFINITIONS = [RecordingDefinition(paths.example_700KB), RecordingDefinition(paths.gambling)]  # All those on disk.

    def __post_init__(self):
        # super().__post_init__()
        self.controls = [self.select_recording, self.btn_change_theme]

    @cached_property
    def select_recording(self):
        return SelectRecording(name="Recordings", options=[str(defin.path) for defin in self.DEFINITIONS])

    @cached_property
    def btn_change_theme(self):
        return ButtonChangeTheme(name="Change Theme")



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
    device = Amniotic(name=f"{Constants.DEVELOPMENT} Amniotic")

    client = ClientAmniotic(hostname=MQTT_HOST, device=device, logger=logging.getLogger(__name__))
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
