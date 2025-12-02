import homeassistant_api
from dataclasses import dataclass
from dataclasses import field, fields
from functools import cached_property
from typing import Self

from amniotic.controls import SelectTheme, SelectRecording, PlayRecording, NumberVolume, SelectMediaPlayer, PlayStreamButton, StreamURL
from amniotic.recording import RecordingMetadata
from amniotic.theme import ThemeDefinition
from fmtr.tools import Path
from fmtr.tools.iterator_tools import IndexList
from haco.device import Device


@dataclass
class MediaState:
    entity_id: str
    state: str
    friendly_name: str
    media_content_type: str
    media_duration: int
    media_position: int
    media_position_updated_at: str
    supported_features: int
    volume_level: float

    @classmethod
    def from_state(cls, state) -> Self:
        data = state.model_dump()
        data |= data.pop('attributes')
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        self = cls(**filtered)
        return self


@dataclass(kw_only=True)
class Amniotic(Device):
    themes: list[ThemeDefinition] = field(default_factory=list, metadata=dict(exclude=True))
    theme_current: ThemeDefinition = field(default=None, metadata=dict(exclude=True))
    client_ha: homeassistant_api.Client = field(default=None, metadata=dict(exclude=True))

    path_audio_str: str = field(metadata=dict(exclude=True))

    def __post_init__(self):
        self.metas = IndexList(RecordingMetadata(path) for path in self.path_audio.iterdir())  # All those on disk.
        self.meta_current = next(iter(self.metas))

        self.themes = IndexList(self.themes)

        theme = ThemeDefinition(amniotic=self, name='Default A')
        self.themes.append(theme)
        self.theme_current: ThemeDefinition = theme

        theme = ThemeDefinition(amniotic=self, name='Default B')
        self.themes.append(theme)

        media_players_data = [state for state in self.client_ha.get_states() if state.entity_id.startswith("media_player.")]
        self.media_player_states = IndexList(MediaState.from_state(data) for data in media_players_data)
        self.media_player_current = next(iter(self.media_player_states))

        self.controls = [self.select_recording, self.select_theme, self.swt_play, self.nbr_volume, self.select_media_player, self.btn_play, self.sns_url]

    @cached_property
    def path_audio(self):
        return Path(self.path_audio_str)

    @cached_property
    def select_theme(self):
        return SelectTheme(name="Themes", options=[str(defin.name) for defin in self.themes])

    @cached_property
    def select_recording(self):
        return SelectRecording(name="Recordings", options=[str(meta.name) for meta in self.metas])

    @cached_property
    def select_media_player(self):
        return SelectMediaPlayer(name="Media Player", options=list(self.media_player_states.entity_id.keys()))

    @cached_property
    def swt_play(self):
        return PlayRecording(name="Play")

    @cached_property
    def btn_play(self):
        return PlayStreamButton(name="Play Stream")

    @cached_property
    def sns_url(self):
        return StreamURL(name="Stream URL")

    @cached_property
    def nbr_volume(self):
        return NumberVolume(name="Volume")


