import asyncio
from pydantic import Field

from amniotic.client import ClientAmniotic
from amniotic.device import Amniotic
from amniotic.paths import paths
from fmtr.tools import sets, mqtt


class Settings(sets.Base):
    paths = paths

    home_assistant_url: str = Field(alias="HOME_ASSISTANT_URL")
    hassio_token: str = Field(alias="HASSIO_TOKEN")

    stream_url: str
    name: str = Amniotic.__name__
    mqtt: mqtt.Client.Args
    path_audio: str = str(paths.audio)

    def run(self):
        super().run()
        asyncio.run(self.run_async())

    async def run_async(self):
        from fmtr.tools import debug
        debug.trace()
        from fmtr import tools
        from amniotic.obs import logger
        from amniotic.paths import paths
        from amniotic.version import __version__

        logger.info(f'Launching {paths.name_ns} {__version__=} {tools.get_version()=} from entrypoint.')
        logger.debug(f'{paths.settings.exists()=} {str(paths.settings)=}')

        logger.info(f'Launching...')
        import homeassistant_api
        client_ha = homeassistant_api.Client(self.home_assistant_url, self.hassio_token)
        device = Amniotic(name=self.name, client_ha=client_ha, path_audio_str=self.path_audio, sw_version=__version__, manufacturer=paths.org_singleton, model=Amniotic.__name__)
        client = ClientAmniotic.from_args(self.mqtt, device=device)
        await client.start()

settings = Settings()
settings
