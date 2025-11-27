from dataclasses import dataclass

from haco.button import Button
from haco.number import Number
from haco.select import Select
from haco.switch import Switch


@dataclass(kw_only=True)
class SelectTheme(Select):

    async def command(self, value):
        self.device.set_theme(value)
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

    async def command(self, value):
        self.device.theme_current.instance_current.volume = value / 100


    async def state(self, value=None):
        return int(self.device.theme_current.instance_current.volume * 100)


@dataclass(kw_only=True)
class SelectMediaPlayer(Select):
    async def command(self, value):
        state = self.device.media_player_lookup[value]
        self.device.media_player_current = state
        return value

    async def state(self, value):
        return self.device.media_player_current.entity_id


@dataclass(kw_only=True)
class PlayStreamButton(Button):
    def command(self, value):
        media_player = self.device.client_ha.get_domain("media_player")
        media_player.play_media(
            entity_id=self.device.media_player_current.entity_id,
            media_content_id=f'https://amniotic.ws.gex.fmtr.dev/stream/{self.device.theme_current.id}',
            media_content_type="music",
        )
