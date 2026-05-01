import asyncio
import homeassistant_api
import psutil
from dataclasses import dataclass
from dataclasses import fields
from functools import cached_property
from typing import Self

from amniotic.controls import SelectTheme, SelectRecording, EnableRecording, NumberVolume, SelectMediaPlayer, PlayStreamButton, StreamURL, NewTheme, DeleteTheme, DownloadLink, DownloadStatus, DownloadPercent, RecordingsPresent, ThemeStreamable
from amniotic.ha_api import client_ha
from amniotic.obs import logger
from amniotic.recording import RecordingMetadata
from amniotic.theme import ThemeDefinition, IndexThemes
from corio import Path
from corio.iterator_tools import IndexList, IterDiffer
from haco.device import Device
from pydantic import Field


@dataclass
class MediaState:
    entity_id: str
    state: str
    friendly_name: str | None = None
    supported_features: int | None = None

    def __post_init__(self):
        self.friendly_name = self.friendly_name or self.entity_id

    @classmethod
    def from_state(cls, data) -> Self:
        data |= data.pop('attributes')
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        self = cls(**filtered)
        return self


class Amniotic(Device):
    themes: IndexList[ThemeDefinition] = Field(default_factory=IndexList, exclude=True, repr=False)
    metas: IndexList[RecordingMetadata] = Field(default_factory=IndexList, exclude=True, repr=False)
    media_player_states: IndexList[MediaState] = Field(default_factory=IndexList, exclude=True, repr=False)

    client_ha: homeassistant_api.Client | None = Field(default=None, exclude=True, repr=False)

    path_audio: Path = Field(exclude=True, repr=False)
    path_audio_schedule_duration: int = Field(default=10, exclude=True, repr=False)

    path_audio_schedule_task: asyncio.Task | None = Field(default=None, exclude=True, repr=False)

    monitor_interval: int = Field(default=30, exclude=True, repr=False)
    monitor_task: asyncio.Task | None = Field(default=None, exclude=True, repr=False)

    def model_post_init(self, __context):
        if not self.path_audio.exists():
            logger.warning(f'Audio path "{self.path_audio}" does not exist. Will be created.')
            self.path_audio.mkdir()
        self.metas = IndexList()
        self.refresh_metas()

        if not self.metas:
            logger.warning(f'No audio files found in "{self.path_audio}". You will need to add some before you can stream anything.')

        self.themes = IndexThemes.load(self)

        self.media_player_states = IndexList(self.get_media_players())

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

        logger.debug(f'Refreshing Recordings from "{self.path_audio}"...')

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

        if not loop:
            return await self._refresh_metas_task_logic()

        while True:
            try:
                await asyncio.sleep(self.path_audio_schedule_duration)
                await self._refresh_metas_task_logic()
            except Exception:
                logger.exception('Error in background audio file monitoring task.')

    async def _refresh_metas_task_logic(self):
        try:
            is_changed = self.refresh_metas()
            if is_changed:
                logger.info(f'Audio file monitoring task found changes. Directory: "{self.path_audio}"...')
                await self.bsn_recordings_present.state()
                await self.select_recording.state()
        except Exception:
            logger.exception('Error in audio file monitoring task logic.')

    async def monitor_objects_task(self):
        try:
            import gc
            import sys
            import psutil
            from corio import av
            from amniotic.theme import ThemeDefinition, ThemeStream
            from amniotic.recording import RecordingMetadata, RecordingThemeInstance, RecordingThemeStream
            from av.container.input import InputContainer
            from av.container.output import OutputContainer

            process = psutil.Process()

            classes = (
                ThemeDefinition, ThemeStream, RecordingMetadata, RecordingThemeInstance, RecordingThemeStream,
                InputContainer, OutputContainer
            )

            while True:
                try:
                    mem = process.memory_info()
                    threads = process.num_threads()
                    logger.debug(f'MoniOTel: Process rss={mem.rss} vms={mem.vms} threads={threads}')

                    counts = {cls.__name__: 0 for cls in classes}
                    sizes = {cls.__name__: 0 for cls in classes}

                    for obj in gc.get_objects():
                        for cls in classes:
                            if isinstance(obj, cls):
                                counts[cls.__name__] += 1
                                sizes[cls.__name__] += sys.getsizeof(obj)

                    for name in counts:
                        count = counts[name]
                        size = sizes[name]
                        logger.debug(f'MoniOTel: {name} count={count} size={size}')

                except Exception:
                    logger.exception('Error in object monitoring task loop.')

                await asyncio.sleep(self.monitor_interval)

        except Exception:
            logger.exception('Fatal error in object monitoring task initialization.')

    @logger.instrument('Refreshing Media Player Entities from HA API...')
    def get_media_players(self) -> list[MediaState]:

        response = client_ha.get(
            f"{client_ha.url_api}/states",
            headers=client_ha.headers_auth,
        )

        response.raise_for_status()
        data_all = response.json()
        data_mps = [datum for datum in data_all if datum["entity_id"].startswith("media_player.")]
        objs = [MediaState.from_state(datum) for datum in data_mps]

        logger.info(f'Found {len(objs)} Media Player Entities.')
        return objs

    async def initialise(self):
        await super().initialise()
        if not self.path_audio_schedule_task:
            self.path_audio_schedule_task = asyncio.create_task(self.refresh_metas_task())

        if not self.monitor_task:
            self.monitor_task = asyncio.create_task(self.monitor_objects_task())
