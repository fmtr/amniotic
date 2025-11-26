from dataclasses import dataclass

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
