from dataclasses import dataclass

from amniotic.obs import logger
from haco.button import Button
from haco.number import Number
from haco.select import Select
from haco.switch import Switch


@dataclass(kw_only=True)
class SelectTheme(Select):
    icon: str = 'surround-sound'

    async def command(self, value):
        theme = self.device.themes.name[value]
        self.device.theme_current = theme
        return value


    async def state(self, value=None):
        name = self.device.theme_current.name
        await self.device.select_recording.state()
        return name

@dataclass(kw_only=True)
class SelectRecording(Select):

    async def command(self, value):
        self.device.theme_current.set_instance(value)

        return value

    async def state(self, value):
        await self.device.swt_play.state()
        await self.device.nbr_volume.state()
        return self.device.theme_current.instance_current.name




@dataclass(kw_only=True)
class PlayRecording(Switch):

    async def command(self, value):
        self.device.theme_current.instance_current.is_enabled = value

    async def state(self, value=None):
        is_enabled = self.device.theme_current.instance_current.is_enabled
        return is_enabled


@dataclass(kw_only=True)
class NumberVolume(Number):
    icon: str = 'volume-medium'

    async def command(self, value):
        self.device.theme_current.instance_current.volume = value / 100


    async def state(self, value=None):
        return int(self.device.theme_current.instance_current.volume * 100)


@dataclass(kw_only=True)
class SelectMediaPlayer(Select):
    async def command(self, value):
        state = self.device.media_player_states.entity_id[value]
        self.device.media_player_current = state
        return value

    async def state(self, value):
        return self.device.media_player_current.entity_id


@dataclass(kw_only=True)
class PlayStreamButton(Button):
    def command(self, value):
        media_player = self.device.client_ha.get_domain("media_player")

        with logger.span(f'Sending play_media to {self.device.media_player_current.entity_id}: {self.device.theme_current.url}'):
            media_player.play_media(
                entity_id=self.device.media_player_current.entity_id,
                media_content_id=self.device.theme_current.url,
                media_content_type="channel",
                extra=dict(title=self.device.theme_current.name)
            )
