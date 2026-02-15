import asyncio

from amniotic.api import ApiAmniotic
from amniotic.device import Amniotic
from amniotic.obs import logger
from corio import http
from haco.client import ClientHaco


class ClientAmniotic(ClientHaco):
    """
    Take an extra API argument, and gather with super.start
    """

    API_CLASS = ApiAmniotic

    def __init__(self, device: Amniotic, *args, **kwargs):
        super().__init__(device=device, *args, **kwargs)

    async def start(self):
        logger.info(f'Connecting MQTT client to {self._client.username}@{self._hostname}:{self._port}...')
        await asyncio.gather(
            super().start(),
            self.API_CLASS.launch_async(self)
        )

    @classmethod
    @logger.instrument('Instantiating MQTT client from Supervisor API...')
    def from_supervisor(cls, device: Amniotic, **kwargs):
        from amniotic.settings import settings

        response = http.client.get(
                f"{settings.ha_supervisor_api}/services/mqtt",
                headers={
                    "Authorization": f"Bearer {settings.token}",
                    "Content-Type": "application/json",
                },
            )

        data = response.json().get("data", {})

        if not data.get("host"):
            msg = "MQTT service not found in Supervisor API. See https://fmtr.link/amniotic/doc/mqtt for how to install an MQTT broker."
            raise RuntimeError(msg)

        self = cls(device=device, hostname=data['host'], port=data['port'], username=data['username'], password=data['password'], **kwargs)
        return self
