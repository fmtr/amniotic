from dataclasses import dataclass

from amniotic.obs import logger
from haco.button import Button
from haco.control import Control
from haco.number import Number
from haco.select import Select
from haco.sensor import Sensor
from haco.switch import Switch


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
    icon: str = 'surround-sound'
    name: str = 'Theme'

    @logger.instrument('Setting Theme to "{value}"...')
    async def command(self, value):
        theme = self.themes.name[value]
        self.themes.current = theme
        return value


    async def state(self, value=None):
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

    def command(self, value):
        media_player = self.device.client_ha.get_domain("media_player")
        state = self.device.media_player_states.current

        if not state:
            return

        with logger.span(f'Sending play_media to {state.entity_id}: {self.theme.url}'):
            media_player.play_media(
                entity_id=state.entity_id,
                media_content_id=self.theme.url,
                media_content_type="channel",
                extra=dict(title=self.theme.name)
            )
