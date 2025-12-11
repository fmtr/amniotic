from dataclasses import dataclass

from amniotic.obs import logger
from amniotic.theme import ThemeDefinition
from fmtr.tools import http
from haco.button import Button
from haco.control import Control
from haco.number import Number
from haco.select import Select
from haco.sensor import Sensor
from haco.switch import Switch
from haco.text import Text


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

        options = sorted(self.themes.name.keys())
        if self.options != options:
            self.options = options
            await self.announce()

        name = self.theme.name

        await self.device.select_recording.state()
        await self.device.sns_url.state()
        return name

@dataclass(kw_only=True)
class SelectRecording(Select, ThemeRelativeControl):
    icon: str = 'waveform'
    name: str = 'Recording'

    @logger.instrument('Setting Theme "{self.theme.name}" current recording instance to "{value}"...')
    async def command(self, value):
        self.instances.current = self.instances.name[value]
        return value

    async def state(self, value):
        await self.device.swt_play.state()
        await self.device.nbr_volume.state()
        if self.instance:
            return self.instance.name
        return None


@dataclass(kw_only=True)
class PlayRecording(Switch, ThemeRelativeControl):
    icon: str = 'playlist-plus'
    name: str = 'Enable Recording'

    @logger.instrument('Toggling {value=} recording instance "{self.instances.current.name}" for Theme "{self.theme.name}"...')
    async def command(self, value):
        self.instance.is_enabled = value

    async def state(self, value=None):
        if self.instance:
            return self.instance.is_enabled
        return None


@dataclass(kw_only=True)
class NumberVolume(Number, ThemeRelativeControl):
    icon: str = 'volume-medium'
    name: str = 'Recording Volume'

    @logger.instrument('Setting volume to {value} for recording instance "{self.instances.current.name}" for Theme "{self.theme.name}"...')
    async def command(self, value):
        if self.instance:
            self.instance.volume = value / 100



    async def state(self, value=None):
        if self.instance:
            return int(self.instance.volume * 100)
        return None


@dataclass(kw_only=True)
class SelectMediaPlayer(Select, ThemeRelativeControl):
    icon: str = 'cast-audio'
    name: str = 'Media Player'

    @logger.instrument('Selecting Media Play "{value}" for Theme "{self.theme.name}"...')
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

    async def command(self, value):
        from amniotic.settings import settings
        state = self.device.media_player_states.current

        if not state:
            return

        with logger.span(f'Sending play_media to {state.entity_id}: {self.theme.url}'):
            url = f"{settings.ha_core_api}/services/media_player/play_media"
            response = http.client.post(
                url,
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
        theme = ThemeDefinition(amniotic=self.device, name=value)
        self.themes.append(theme)
        self.themes.current = theme

        await self.device.select_theme.state()
        return value

    async def state(self, value=None):
        return value or 'new theme!'


@dataclass(kw_only=True)
class DeleteTheme(Button, ThemeRelativeControl):
    icon: str = 'access-point-remove'
    name: str = 'Delete Current Theme'

    @logger.instrument('Deleting Theme "{self.theme.name}"...')
    async def command(self, value):
        self.themes.remove(self.theme)
        await self.device.select_theme.state()
        return value
