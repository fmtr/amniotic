from dataclasses import dataclass, field
from functools import cached_property

from amniotic.obs import logger
from amniotic.paths import paths
from amniotic.v2.controls import SelectTheme, SelectRecording, PlayRecording, NumberVolume
from amniotic.v2.recording import ThemeDefinition, RecordingDefinition
from haco.device import Device


@dataclass(kw_only=True)
class Amniotic(Device):
    themes: list[ThemeDefinition] = field(default_factory=list, metadata=dict(exclude=True))
    theme_current: ThemeDefinition = field(default=None, metadata=dict(exclude=True))

    DEFINITIONS = [RecordingDefinition(paths.example_700KB), RecordingDefinition(paths.gambling)]  # All those on disk.

    def __post_init__(self):
        theme = ThemeDefinition(amniotic=self, name='Default A')
        self.themes.append(theme)
        self.theme_current = theme

        self.recording_current = self.DEFINITIONS[0]

        self.controls = [self.select_recording, self.select_theme, self.swt_play, self.nbr_volume]

    @cached_property
    def select_theme(self):
        return SelectTheme(name="Themes", options=[str(defin.name) for defin in self.themes])

    @cached_property
    def select_recording(self):
        return SelectRecording(name="Recordings", options=[str(defin.path.stem) for defin in self.DEFINITIONS])

    @cached_property
    def swt_play(self):
        return PlayRecording(name="Play")

    @cached_property
    def nbr_volume(self):
        return NumberVolume(name="Volume")

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
