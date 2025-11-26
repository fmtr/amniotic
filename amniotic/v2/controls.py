from dataclasses import dataclass

from haco.number import Number
from haco.select import Select
from haco.switch import Switch


@dataclass(kw_only=True)
class SelectRecording(Select):

    async def command(self, value):
        self.device.set_recording(value)
        await self.device.swt_play.state()
        return value

    async def state(self, value):
        name = self.device.recording_current.name
        return name


@dataclass(kw_only=True)
class SelectTheme(Select):

    async def command(self, value):
        self.device.set_theme(value)
        return value

    async def state(self, value=None):
        name = self.device.theme_current.name
        return name


@dataclass(kw_only=True)
class PlayRecording(Switch):

    async def command(self, value):
        defin = self.device.recording_current

        if value:
            self.device.theme_current.enable(defin)
        else:
            self.device.theme_current.disable(defin)
        return value

    async def state(self, value=None):

        is_enabled = self.device.recording_current in self.device.theme_current.definitions
        return is_enabled


@dataclass(kw_only=True)
class NumberVolume(Number):

    async def command(self, value):
        self.device.set_theme(value)
        return value

    async def state(self, value=None):
        name = self.device.theme_current.name
        return name
