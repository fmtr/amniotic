import asyncio
import shutil
from dataclasses import dataclass, field
from functools import cached_property

from amniotic.obs import logger
from amniotic.recording import RecordingThemeInstance
from amniotic.theme import ThemeDefinition
from fmtr.tools import http, youtube
from haco import binary_sensor
from haco.binary_sensor import BinarySensor
from haco.button import Button
from haco.control import Control
from haco.number import Number
from haco.select import Select
from haco.sensor import Sensor
from haco.switch import Switch
from haco.text import Text
from haco.uom import Uom


@dataclass(kw_only=True)
class ThemeRelativeControl(Control):

    @property
    def themes(self):
        return self.device.themes

    @property
    def theme(self):
        return self.themes.current

    @property
    def instances(self):
        return self.theme.instances

    @property
    def instance(self):
        return self.instances.current


@dataclass(kw_only=True)
class SelectTheme(Select, ThemeRelativeControl):
    icon: str = 'access-point'
    name: str = 'Theme'

    @logger.instrument('Setting Theme to "{value}"...')
    async def command(self, value):
        theme = self.themes.name[value]
        self.themes.current = theme
        return value


    async def state(self, value=None):

        if self.theme not in self.themes:
            if self.themes:
                self.themes.current = next(iter(self.themes))
            else:
                logger.warning('No themes exist. Creating default...')
                theme = ThemeDefinition(amniotic=self.device, name="Default")
                self.themes.append(theme)
                self.themes.current = theme
                self.themes.save()

        options = sorted(self.themes.name.keys())
        if self.options != options:
            self.options = options
            await self.announce()

        name = self.theme.name

        await self.device.select_recording.state()
        await self.device.sns_url.state()
        await self.device.bsn_theme_streamable.state()
        return name

@dataclass(kw_only=True)
class SelectRecording(Select, ThemeRelativeControl):
    icon: str = 'waveform'
    name: str = 'Recording'

    def set_default(self, value):
        instance = self.instances.name.get(value)
        if not instance:
            logger.info(f'Creating new recording instance "{value}" for Theme "{self.theme.name}"...')
            meta = self.device.metas.name[value]
            instance = RecordingThemeInstance(path=meta.path_str, device=self.device)
            self.instances.append(instance)

        self.instances.current = instance
        return instance

    @logger.instrument('Setting Theme "{self.theme.name}" current recording instance to "{value}"...')
    async def command(self, value):
        self.set_default(value)
        return value

    async def state(self, value=None):

        options = sorted(self.device.metas.name.keys())
        if self.options != options:
            self.options = options
            await self.announce()

        if not self.instance:
            if not self.device.metas.current:
                return None

            name = self.device.metas.current.name
            instance = self.set_default(name)

        await self.device.swt_play.state()
        await self.device.nbr_volume.state()
        return self.instance.name



@dataclass(kw_only=True)
class EnableRecording(Switch, ThemeRelativeControl):
    icon: str = 'playlist-plus'
    name: str = 'Enable Recording'

    @logger.instrument('Toggling {value=} recording instance "{self.instances.current.name}" for Theme "{self.theme.name}"...')
    async def command(self, value):

        if not self.instance:
            return None

        self.instance.is_enabled = value
        self.themes.save()


    async def state(self, value=None):

        if not self.instance:
            return None

        await self.device.bsn_theme_streamable.state()
        return self.instance.is_enabled



@dataclass(kw_only=True)
class NumberVolume(Number, ThemeRelativeControl):
    icon: str = 'volume-medium'
    name: str = 'Recording Volume'

    @logger.instrument('Setting volume to {value} for recording instance "{self.instances.current.name}" for Theme "{self.theme.name}"...')
    async def command(self, value):

        if not self.instance:
            return None

        self.instance.volume = value / 100
        self.themes.save()


    async def state(self, value=None):

        if not self.instance:
            return None


        return int(self.instance.volume * 100)



@dataclass(kw_only=True)
class SelectMediaPlayer(Select, ThemeRelativeControl):
    icon: str = 'cast-audio'
    name: str = 'Media Player'

    @logger.instrument('Selecting Media Player "{value}" for Theme "{self.theme.name}"...')
    async def command(self, value):
        state = self.device.media_player_states.friendly_name[value]
        self.device.media_player_states.current = state
        return value

    async def state(self, value):
        player = self.device.media_player_states.current
        if player:
            return player.friendly_name
        return None


@dataclass(kw_only=True)
class StreamURL(Sensor, ThemeRelativeControl):
    icon: str = 'link-variant'
    name: str = 'Stream URL'

    async def state(self, value=None):
        return self.theme.url


@dataclass(kw_only=True)
class PlayStreamButton(Button, ThemeRelativeControl):
    icon: str = 'play-network'
    name: str = 'Stream'

    @property
    def url_api(self):
        from amniotic.settings import settings

        return f"{settings.ha_core_api}/services/media_player/play_media"


    async def command(self, value):

        if not self.instance:
            return None

        state = self.device.media_player_states.current

        if not state:
            return

        with logger.span(f'Posting request to HA API {self.url_api} {state.entity_id=} {self.theme.url=}') as span:
            try:
                await self.post(state)
            except Exception as exception:
                logger.error(f'Error posting to HA API: {repr(exception)}.')
                span.record_exception(exception=exception)

    async def post(self, state):
        from amniotic.settings import settings

        response = http.client.post(
            self.url_api,
            headers={
                "Authorization": f"Bearer {settings.token}",
                "Content-Type": "application/json",
            },
            json={
                "entity_id": state.entity_id,
                "media_content_id": self.theme.url,
                "media_content_type": "music",
            }
        )

        response.raise_for_status()


@dataclass(kw_only=True)
class NewTheme(Text, ThemeRelativeControl):
    icon: str = 'access-point-plus'
    name: str = 'New Theme'

    @logger.instrument('Creating new Theme "{value}"...')
    async def command(self, value):
        if not value:
            return

        theme = ThemeDefinition(amniotic=self.device, name=value)
        self.themes.append(theme)
        self.themes.current = theme
        self.themes.save()

        await self.device.select_theme.state()

    async def state(self, value=None):
        return 'My New Theme'


@dataclass(kw_only=True)
class DeleteTheme(Button, ThemeRelativeControl):
    icon: str = 'access-point-remove'
    name: str = 'Delete Current Theme'

    @logger.instrument('Deleting Theme "{self.theme.name}"...')
    async def command(self, value):
        self.themes.remove(self.theme)
        self.themes.save()
        await self.device.select_theme.state()
        return value


@dataclass(kw_only=True)
class DownloadLink(Text):
    """

    YouTube audio stream downloader URL input.

    """

    icon: str = 'cloud-download-outline'
    name: str = 'Download from YouTube'
    downloader: youtube.AudioStreamDownloader | None = field(default=None, metadata=dict(exclude=True))

    @cached_property
    def status_state(self):
        return self.device.sns_download_status.state

    @cached_property
    def percent_state(self):
        return self.device.sns_download_percent.state

    @logger.instrument('Downloading YouTube Link "{value}"...')
    async def command(self, value):
        asyncio.create_task(self.download(value))
        return value

    async def state(self, value=None):
        return value or ''

    @logger.instrument('Downloading "{url}"...')
    async def download(self, url: str):

        if self.downloader:
            message = f'Cannot download "{url}". Downloader already running.'
            logger.warning(message)
            await self.status_state(value=message)
            return None

        self.downloader = youtube.AudioStreamDownloader(url_or_id=url)

        try:
            async for data in self.downloader.download():

                if data.message:
                    logger.info(data.message)
                    await self.status_state(value=data.message)
                if data.percentage is not None:
                    message = f"Downloading: {data.percentage}% complete..."
                    logger.info(message)
                    await self.percent_state(value=data.percentage)

            await self.status_state(value='Moving download to audio directory...')
            src = self.downloader.path
            dst = self.device.path_audio / src.name
            shutil.move(src, dst)
            await self.device.refresh_metas_task(loop=False)
            await self.device.select_recording.state()

            await self.status_state(value='Finished')

        except Exception as exception:
            message = 'Error downloading. See container logs for details.'
            logger.error(message)
            await self.status_state(value=message)
            raise exception
        finally:
            await self.status_state(value=None)
            await self.percent_state(value=None)
            self.downloader = None


@dataclass(kw_only=True)
class DownloadStatus(Sensor):
    icon: str = 'cloud-sync-outline'
    name: str = 'Download Status'

    async def state(self, value=None):
        return value or 'Idle'


@dataclass(kw_only=True)
class DownloadPercent(Sensor):
    icon: str = 'cloud-percent-outline'
    name: str = 'Download Percent Complete'
    unit_of_measurement: Uom = Uom.PERCENTAGE

    async def state(self, value=None):
        return value or 0


@dataclass(kw_only=True)
class RecordingsPresent(BinarySensor):
    icon: str = 'waves'
    name: str = 'Recordings Present'

    async def state(self, value=None):
        value = bool(self.device.metas)
        return value


@dataclass(kw_only=True)
class ThemeStreamable(BinarySensor, ThemeRelativeControl):
    icon: str = 'volume-vibrate'
    name: str = 'Theme Streamable'
    device_class = binary_sensor.DeviceClass.SOUND

    async def state(self, value=None):
        value = self.theme.is_enabled
        return value
