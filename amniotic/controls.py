from dataclasses import dataclass

from amniotic.obs import logger
from haco.button import Button
from haco.number import Number
from haco.select import Select
from haco.sensor import Sensor
from haco.switch import Switch


@dataclass(kw_only=True)
class SelectTheme(Select):
    icon: str = 'surround-sound'

    async def command(self, value):
        theme = self.device.themes.name[value]
        self.device.themes.current = theme
        return value


    async def state(self, value=None):
        name = self.device.themes.current.name
        await self.device.select_recording.state()
        await self.device.sns_url.state()
        return name

@dataclass(kw_only=True)
class SelectRecording(Select):

    # @logger.instrument('Setting Theme "{self.name}" current recording instance to "{name}"...')
    async def command(self, value):
        self.device.themes.current.instances.current = self.device.themes.current.instances.name[value]

        return value

    async def state(self, value):
        await self.device.swt_play.state()
        await self.device.nbr_volume.state()
        return self.device.themes.current.instances.current.name




@dataclass(kw_only=True)
class PlayRecording(Switch):

    async def command(self, value):
        self.device.themes.current.instances.current.is_enabled = value

    async def state(self, value=None):
        is_enabled = self.device.themes.current.instances.current.is_enabled
        return is_enabled


@dataclass(kw_only=True)
class NumberVolume(Number):
    icon: str = 'volume-medium'

    async def command(self, value):
        self.device.themes.current.instances.current.volume = value / 100


    async def state(self, value=None):
        return int(self.device.themes.current.instances.current.volume * 100)


@dataclass(kw_only=True)
class SelectMediaPlayer(Select):
    async def command(self, value):
        state = self.device.media_player_states.entity_id[value]
        self.device.media_player_states.current = state
        return value

    async def state(self, value):
        return self.device.media_player_states.current.entity_id


@dataclass(kw_only=True)
class StreamURL(Sensor):
    nane: str = 'Current Stream URL'

    async def state(self, value=None):
        return self.device.themes.current.url


@dataclass(kw_only=True)
class PlayStreamButton(Button):
    def command(self, value):
        media_player = self.device.client_ha.get_domain("media_player")

        state = self.device.media_player_states.current
        theme = self.device.themes.current

        with logger.span(f'Sending play_media to {state.entity_id}: {theme.url}'):
            media_player.play_media(
                entity_id=state.entity_id,
                media_content_id=theme.url,
                media_content_type="channel",
                extra=dict(title=theme.name)
            )
