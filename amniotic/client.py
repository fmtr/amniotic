import asyncio

from amniotic.api import ApiAmniotic
from amniotic.device import Amniotic
from amniotic.obs import logger
from haco.client import ClientHaco


class ClientAmniotic(ClientHaco):
    """
    Take an extra API argument, and gather with super.start
    """

    API_CLASS = ApiAmniotic

    def __init__(self, device: Amniotic, *args, **kwargs):
        super().__init__(device=device, *args, **kwargs)

    @logger.instrument('Starting MQTT client {self.username}@{self.hostname}:{self.port}...')
    async def start(self):
        await asyncio.gather(
            super().start(),
            self.API_CLASS.launch_async(self)
        )
