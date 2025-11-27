from dataclasses import dataclass, field
from functools import cached_property

from amniotic.obs import logger
from amniotic.paths import paths
from amniotic.v2.controls import SelectTheme, SelectRecording, PlayRecording, NumberVolume
from amniotic.v2.recording import RecordingMetadata
from amniotic.v2.theme import ThemeDefinition
from haco.device import Device


@dataclass(kw_only=True)
class Amniotic(Device):
    themes: list[ThemeDefinition] = field(default_factory=list, metadata=dict(exclude=True))
    theme_current: ThemeDefinition = field(default=None, metadata=dict(exclude=True))



    def __post_init__(self):
        self.metas = [RecordingMetadata(path) for path in paths.audio.iterdir()]  # All those on disk.
        self.meta_current = next(iter(self.metas))


        theme = ThemeDefinition(amniotic=self, name='Default A')
        self.themes.append(theme)
        self.theme_current: ThemeDefinition = theme

        theme = ThemeDefinition(amniotic=self, name='Default B')
        self.themes.append(theme)



        self.controls = [self.select_recording, self.select_theme, self.swt_play, self.nbr_volume]

    @cached_property
    def select_theme(self):
        return SelectTheme(name="Themes", options=[str(defin.name) for defin in self.themes])

    @cached_property
    def select_recording(self):
        return SelectRecording(name="Recordings", options=[str(meta.name) for meta in self.metas])

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
    def theme_lookup_id(self):
        return {theme.id: theme for theme in self.themes}

    @logger.instrument('Setting current Theme to "{name}"...')
    def set_theme(self, name):
        theme = self.theme_lookup[name]
        self.theme_current = theme
