import asyncio
import homeassistant_api
from dataclasses import dataclass
from dataclasses import field, fields
from functools import cached_property
from typing import Self

from amniotic.controls import SelectTheme, SelectRecording, EnableRecording, NumberVolume, SelectMediaPlayer, PlayStreamButton, StreamURL, NewTheme, DeleteTheme, DownloadLink, DownloadStatus, DownloadPercent, RecordingsPresent, ThemeStreamable
from amniotic.obs import logger
from amniotic.recording import RecordingMetadata
from amniotic.theme import ThemeDefinition, IndexThemes
from fmtr.tools import Path
from fmtr.tools.iterator_tools import IndexList, IterDiffer
from haco.device import Device


@dataclass
class MediaState:
    entity_id: str
    state: str
    friendly_name: str | None = None
    supported_features: int | None = None

    def __post_init__(self):
        self.friendly_name = self.friendly_name or self.entity_id

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
    themes: IndexList[ThemeDefinition] = field(default_factory=IndexList, metadata=dict(exclude=True))
    metas: IndexList[RecordingMetadata] = field(default_factory=IndexList, metadata=dict(exclude=True))

    client_ha: homeassistant_api.Client | None = field(default=None, metadata=dict(exclude=True))

    path_audio: Path = field(metadata=dict(exclude=True))
    path_audio_schedule_duration: int = field(default=10, metadata=dict(exclude=True))

    path_audio_schedule_task: asyncio.Task | None = field(default=None, metadata=dict(exclude=True))

    def __post_init__(self):
        if not self.path_audio.exists():
            logger.warning(f'Audio path "{self.path_audio}" does not exist. Will be created.')
            self.path_audio.mkdir()
        self.metas = IndexList()
        self.refresh_metas()

        if not self.metas:
            logger.warning(f'No audio files found in "{self.path_audio}". You will need to add some before you can stream anything.')

        self.themes = IndexThemes.load(self)


        media_players_data = [state for state in self.client_ha.get_states() if state.entity_id.startswith("media_player.")]
        self.media_player_states = IndexList(MediaState.from_state(data) for data in media_players_data)

        self.controls = [
            self.select_theme,
            self.select_recording,
            self.btn_delete_theme,
            self.txt_new_theme,
            self.swt_play,
            self.nbr_volume,
            self.select_media_player,
            self.btn_play,
            self.sns_url,
            self.txt_download,
            self.sns_download_status,
            self.sns_download_percent,
            self.bsn_recordings_present,
            self.bsn_theme_streamable,
        ]


    @cached_property
    def select_theme(self):
        return SelectTheme(options=[str(defin.name) for defin in self.themes])

    @cached_property
    def select_recording(self):
        return SelectRecording(options=sorted(self.metas.name.keys()))

    @cached_property
    def select_media_player(self):
        return SelectMediaPlayer(options=list(self.media_player_states.friendly_name.keys()))

    @cached_property
    def swt_play(self):
        return EnableRecording()

    @cached_property
    def btn_play(self):
        return PlayStreamButton()

    @cached_property
    def sns_url(self):
        return StreamURL()

    @cached_property
    def nbr_volume(self):
        return NumberVolume()

    @cached_property
    def txt_new_theme(self):
        return NewTheme()

    @cached_property
    def btn_delete_theme(self):
        return DeleteTheme()

    @cached_property
    def txt_download(self):
        return DownloadLink()

    @cached_property
    def sns_download_status(self):
        return DownloadStatus()

    @cached_property
    def sns_download_percent(self):
        return DownloadPercent()

    @cached_property
    def bsn_recordings_present(self):
        return RecordingsPresent()

    @cached_property
    def bsn_theme_streamable(self):
        return ThemeStreamable()

    def refresh_metas(self) -> bool:

        paths_existing = self.metas.path.keys()
        paths_disk = {path for path in self.path_audio.iterdir() if path.is_file()}

        diff = IterDiffer(paths_existing, paths_disk)

        for path in diff.added:
            logger.info(f'Adding new recording: "{path}"...')
            meta = RecordingMetadata(path)
            self.metas.append(meta)
            if not self.metas.current:
                self.metas.current = meta

        return bool(diff.added)

    async def refresh_metas_task(self, loop=True):

        while loop:
            await asyncio.sleep(self.path_audio_schedule_duration)
            await self.refresh_metas_task(loop=False)
            return

        is_changed = self.refresh_metas()
        if is_changed:
            logger.info(f'Audio file monitoring task found changes. Directory: "{self.path_audio}"...')
            await self.bsn_recordings_present.state()
            await self.select_recording.state()

    async def initialise(self):
        await super().initialise()
        if not self.path_audio_schedule_task:
            self.path_audio_schedule_task = asyncio.create_task(self.refresh_metas_task())