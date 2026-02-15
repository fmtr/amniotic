import asyncio
from fmtr import tools
from functools import cached_property
from pydantic import Field

from amniotic.client import ClientAmniotic
from amniotic.device import Amniotic
from amniotic.paths import paths
from corio import sets, ha, Path, Constants


class Settings(sets.Base):

    paths = paths

    ha_core_api: str = Field(default=ha.constants.URL_CORE_ADDON)
    ha_supervisor_api: str = Field(default=ha.constants.URL_SUPERVISOR_ADDON)

    token: str = Field(alias=ha.constants.SUPERVISOR_TOKEN_KEY)

    stream_url: str
    name: str = Amniotic.__name__
    mqtt: tools.mqtt.Client.Args | None = None

    path_audio: Path
    path_config: Path = ha.constants.PATH_ADDON_CONFIG / Amniotic.__name__.lower()  # todo make add-specific defaults on settings subclass

    @cached_property
    def path_themes(self):
        return self.path_config / 'themes.json'

    def run(self):
        super().run()
        asyncio.run(self.run_async())

    async def run_async(self):
        from corio import debug
        debug.trace()
        import corio

        from amniotic.obs import logger
        from amniotic.paths import paths

        logger.info(f'Launching {paths.name_ns} {paths.metadata.version=} {corio.get_version()=} from entrypoint.')
        logger.debug(f'{paths.settings.exists()=} {str(paths.settings)=}')

        logger.info(f'Launching...')

        if not self.path_config.exists():
            logger.warning(f'Config directory does not exist at "{self.path_config}". Will be created.')
            self.path_config.mkdir()

        client_ha = ha.core.Client(api_url=self.ha_core_api, token=self.token)
        device = Amniotic(name=self.name, client_ha=client_ha, path_audio=self.path_audio, sw_version=paths.metadata.version, manufacturer=Constants.ORG_NAME, model=Amniotic.__name__)

        if self.mqtt:
            client = ClientAmniotic.from_args(self.mqtt, device=device)
        else:
            client = ClientAmniotic.from_supervisor(device=device)

        await client.start()


ha.apply_addon_env()
settings = Settings()
settings
