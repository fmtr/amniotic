import asyncio
from dataclasses import dataclass, field
from functools import cached_property

from amniotic.obs import logger
from amniotic.paths import paths
from amniotic.v2.api import ApiAmniotic
from amniotic.v2.recording import RecordingDefinition, ThemeDefinition
from fmtr.tools import Constants
from haco.client import ClientHaco
from haco.constants import MQTT_HOST
from haco.device import Device
from haco.select import Select
from haco.switch import Switch


@dataclass(kw_only=True)
class Amniotic(Device):
    themes: list[ThemeDefinition] = field(default_factory=list, metadata=dict(exclude=True))
    theme_current: ThemeDefinition = field(default=None, metadata=dict(exclude=True))

    DEFINITIONS = [RecordingDefinition(paths.example_700KB), RecordingDefinition(paths.gambling)]  # All those on disk.

    def __post_init__(self):
        theme = ThemeDefinition(amniotic=self, name='theme A')
        self.themes.append(theme)
        self.theme_current = theme

        self.recording_current = self.DEFINITIONS[0]

        self.controls = [self.select_recording, self.select_theme, self.swt_play]

    @cached_property
    def select_theme(self):
        return SelectTheme(name="Themes", options=[str(defin.name) for defin in self.themes])

    @cached_property
    def select_recording(self):
        return SelectRecording(name="Recordings", options=[str(defin.path.stem) for defin in self.DEFINITIONS])

    @cached_property
    def swt_play(self):
        return PlayRecording(name="Play")

    @property
    def theme_lookup(self):
        return {theme.name: theme for theme in self.themes}

    @property
    def recording_lookup(self):
        return {defin.name: defin for defin in self.DEFINITIONS}

    @logger.instrument('Setting current recording to {name}...')
    def set_recording(self, name):
        defin = self.recording_lookup[name]
        self.recording_current = defin

    def set_theme(self, name):
        theme = self.theme_lookup[name]
        self.theme_current = theme


@dataclass(kw_only=True)
class SelectRecording(Select):

    def command(self, value):
        self.device.set_recording(value)
        return value


@dataclass(kw_only=True)
class SelectTheme(Select):

    async def command(self, value):
        self.device.set_theme(value)
        return value


@dataclass(kw_only=True)
class PlayRecording(Switch):

    async def command(self, value):
        defin = self.device.recording_current
        self.device.theme_current.enable(defin)
        return value

    async def state(self, value):
        return value


class ClientAmniotic(ClientHaco):
    """
    Take an extra API argument, and gather with super.start
    """

    API_CLASS = ApiAmniotic

    def __init__(self, device: Amniotic, *args, **kwargs):
        super().__init__(device=device, *args, **kwargs)

    async def start(self):
        await asyncio.gather(
            super().start(),
            self.API_CLASS.launch_async(self)
        )


async def main():
    device = Amniotic(name=f"{Constants.DEVELOPMENT} Amniotic")
    client = ClientAmniotic(hostname=MQTT_HOST, device=device)
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
