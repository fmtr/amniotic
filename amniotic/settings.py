import asyncio

from amniotic.paths import paths
from fmtr.tools import sets, Constants


class Settings(sets.Base):
    paths = paths

    # mqtt: mqtt.Client.Args

    def run(self):
        super().run()
        asyncio.run(self.run_async())

    async def run_async(self):
        from fmtr.tools import debug, env
        debug.trace()
        from fmtr import tools
        from amniotic.obs import logger
        from amniotic.paths import paths
        from amniotic.version import __version__

        logger.info(f'Launching {paths.name_ns} {__version__=} {tools.get_version()=} from entrypoint.')
        logger.debug(f'{paths.settings.exists()=} {str(paths.settings)=}')

        logger.info(f'Launching...')
        from amniotic.client import ClientAmniotic
        from amniotic.device import Amniotic
        import homeassistant_api

        HA_URL = env.get("HOME_ASSISTANT_URL")
        HA_TOKEN = env.get("HASSIO_TOKEN")

        client_ha = homeassistant_api.Client(HA_URL, HA_TOKEN)

        device = Amniotic(name=f"{Constants.DEVELOPMENT.capitalize()} Amniotic", client_ha=client_ha)

        from haco.constants import MQTT_HOST
        client = ClientAmniotic(hostname=MQTT_HOST, device=device)
        await client.start()


settings = Settings()
settings
