import asyncio

from pydantic import Field

from amniotic.client import ClientAmniotic
from amniotic.device import Amniotic
from amniotic.paths import paths
from fmtr import tools
from fmtr.tools import sets, ha


class Settings(sets.Base):
    paths = paths

    core_url: str = Field(default=ha.constants.URL_CORE_ADDON)
    supervisor_url: str = Field(default=ha.constants.URL_SUPERVISOR_ADDON)

    token: str = Field(alias=ha.constants.SUPERVISOR_TOKEN_KEY)


    stream_url: str
    name: str = Amniotic.__name__
    mqtt: tools.mqtt.Client.Args | None = None

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

        client_ha = ha.core.Client(api_url=self.core_url, token=self.token)
        device = Amniotic(name=self.name, client_ha=client_ha, path_audio_str=self.path_audio, sw_version=__version__, manufacturer=paths.org_singleton, model=Amniotic.__name__)

        if self.mqtt:
            client = ClientAmniotic.from_args(self.mqtt, device=device)
        else:
            client = ClientAmniotic.from_supervisor(device=device)

        await client.start()


ha.apply_addon_env()
settings = Settings()
settings
