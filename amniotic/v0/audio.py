import getpass
import logging
from copy import deepcopy
from datetime import datetime
from itertools import cycle
from numbers import Number
from pathlib import Path
from random import choice
from typing import Union, Optional, Dict

import vlc
from cachetools.func import ttl_cache

VLC_VERBOSITY = 0
DEVICES_POLL_PERIOD_SECONDS = 10
STARTUP_DEVICES_LOGGED = False

def load_new_player() -> vlc.MediaPlayer:
    """

    Instantiate a new player.

    """
    instance = vlc.Instance(f'--verbose {VLC_VERBOSITY}')
    player = vlc.MediaPlayer(instance)
    return player


def unload_player(player: vlc.MediaPlayer):
    """

    Close player (and its instance) properly.

    """
    player.stop()
    instance: vlc.Instance = player.get_instance()
    instance.release()
    player.release()


@ttl_cache(ttl=DEVICES_POLL_PERIOD_SECONDS)
def get_devices_raw() -> vlc.AudioOutputDevice:
    """

    When a player is not yet open, we need to open one temporarily to fetch the audio devices. Since this is somewhat
    expensive, here we cache the devices with a limited lifespan, so that this is only done so often.

    """
    logging.info(f'Loaded temporary player to get devices...')
    player = load_new_player()
    devices_raw = player.audio_output_device_enum()
    logging.info(f'Unloading temporary player.')
    unload_player(player)
    return devices_raw


def log_devices(devices):
    global STARTUP_DEVICES_LOGGED
    if not STARTUP_DEVICES_LOGGED:
        logging.info(f'Found devices on startup: {devices}')
        STARTUP_DEVICES_LOGGED = True


def get_devices(player: Optional[vlc.MediaPlayer] = None, device_names: dict[str, str] = None) -> dict[str, str]:
    """

    Create a mapping from audio output device IDs to their friendly names from VLC's peculiar enum format.

    """

    if player:
        devices_raw = player.audio_output_device_enum()
    else:
        devices_raw = get_devices_raw()

    devices_pairs = []
    if devices_raw:
        device_raw = devices_raw
        while device_raw:
            device_raw = device_raw.contents
            description = device_raw.description.decode()
            device = device_raw.device.decode()
            devices_pairs.append((device, description))
            device_raw = device_raw.next

    devices = {}
    device_names = device_names or {}
    counts = {}
    for device_id, description in devices_pairs:
        description = device_names.get(device_id, device_names.get(description, description))
        counts.setdefault(description, 0)
        counts[description] += 1
        if (count := counts[description]) > 1:
            devices[device_id] = f'{description} ({count})'
        else:
            devices[device_id] = description

    log_devices(devices)

    return devices


def sanitize_volume(value: Number) -> int:
    """

    Ensure a volume is an `int` between 0 and 100

    """
    value = round(value)
    value = min(value, 100)
    value = max(value, 0)
    return value


class Amniotic:
    VOLUME_DEFAULT = 10
    THEME_NAME_DEFAULT = 'Default Theme'
    VLC_VERSION = vlc.__libvlc_version__

    def __init__(self, path: Union[Path, str], device_names: Optional[dict[str, str]] = None, presets: Dict = None):
        """

        Read audio directories and instantiate Theme objects

        """

        user = getpass.getuser()
        if user == 'root':
            msg = f'You are running as root. This could cause issues with PulseAudio, unless it is configured in system-wide mode.'
            logging.warning(msg)

        self.device_names = device_names or {}
        self._enabled = True
        self.path = Path(path).absolute()

        self.themes: Dict[str, Theme] = {}
        self.load_themes()
        if not self.themes:
            msg = f'No audio directories found in "{self.path}". Default theme will be created.'
            logging.warning(msg)
            self.add_new_theme(self.THEME_NAME_DEFAULT)

        self.theme_current = None
        self.set_theme(next(iter(self.themes.keys())))

        self.volume_adjust_threshold = 2
        self.volume = 0
        self.set_volume(self.VOLUME_DEFAULT)

        self.presets = deepcopy(presets) or {}  # Ensure changes to Presets don't also affect config.presets
        self.preset_current = None
        self.merge_presets = False

    def load_themes(self):
        """

        Ensure all (and only) Themes in the Themes path are loaded in

        """
        paths_themes = sorted([path.absolute() for path in self.path.glob('*')])
        paths_themes = {path.stem: path for path in paths_themes}

        for name, path in paths_themes.items():

            if name in self.themes.keys():
                continue

            msg = f'Loading new Theme "{name}"'
            logging.info(msg)
            theme = Theme(path, device_names=self.device_names)
            self.themes[name] = theme

        for name in set(self.themes.keys()):

            if name in paths_themes:
                continue

            msg = f'Removing Theme "{name}" as it no longer exists on disk'
            logging.info(msg)
            theme = self.themes.pop(name)

            if theme.enabled:
                msg = f"""Theme "{name}" is enabled (playing) but does not exist on disk, which shouldn't happen"""
                logging.warning(msg)

            theme.enabled = False

    @property
    def devices(self) -> dict[str, str]:
        """

        Get general (system-wide) devices. Just use those of the first Theme.

        """
        return self.theme_current.devices

    @property
    def enabled(self) -> bool:
        """

        Are any Themes enabled?

        """
        return any([theme.enabled for theme in self.themes.values()])

    @enabled.setter
    def enabled(self, value: bool):
        """

        If set to `False`, disable all Themes.

        """
        value = bool(value)
        self._enabled = value

        if not self._enabled:
            for theme in self.themes.values():
                theme.enabled = self._enabled

    def set_theme(self, id: str):
        """

        Set current theme by the specified name/ID.

        """
        if id not in self.themes:
            id = self.theme_current.get_device_id(id)
        self.theme_current = self.themes[id]

    def add_new_theme(self, name: str, set_current: bool = False):
        """

        Add a new, empty theme by the specified name/ID.

        """
        if name not in self.themes:
            path = self.path / name
            path.mkdir(parents=True)
            theme = Theme(path, device_names=self.device_names)
            self.themes[name] = theme
            if set_current:
                self.set_theme(name)

    def set_volume(self, value: int):
        """

        Set Master Volume, and propagate to all Themes.

        """
        value = sanitize_volume(value)
        self.volume = value
        for theme in self.themes.values():
            theme.volume_master = self.volume
            theme.set_volume()

    def set_volume_adjust_threshold(self, value: int):
        self.volume_adjust_threshold = value
        for theme in self.themes.values():
            theme.volume_adjust_threshold = value

    def set_volume_down(self):
        self.set_volume(self.volume - self.volume_adjust_threshold)

    def set_volume_up(self):
        self.set_volume(self.volume + self.volume_adjust_threshold)

    def set_volume_theme(self, value):
        """

        Set the current Theme Volume.

        """
        self.theme_current.set_volume(value)

    @property
    def status(self) -> dict:
        """

        General status information, including that of all themes.

        """
        themes = [theme.status for theme in self.themes.values()]
        data = {'datetime': datetime.now().isoformat(), 'volume': self.volume, 'themes': themes}
        return data

    @property
    def status_text(self) -> str:
        """

        Brief status overview from all Themes

        """

        statuses_themes = [
            theme.status_text for theme in self.themes.values()
            if theme.enabled
        ]
        status_text = ', '.join(statuses_themes) or None
        return status_text

    def get_preset(self) -> Optional[str]:
        """

        Get the currently applied preset name, if it still matches the current settings

        """
        preset_data_current = self.get_preset_data()
        preset_data = self.presets.get(self.preset_current)
        if preset_data != preset_data_current:
            self.preset_current = None
        return self.preset_current

    def get_preset_data(self) -> Dict:
        """

        Get Preset representing current settings, namely, Master and Theme volumes

        """
        preset = {
            # 'volume': self.volume,
            'themes': {
                name: theme.get_preset() for name, theme in self.themes.items()
                if theme.enabled
            }
        }
        return preset

    def apply_preset(self, name: str):
        """

        Apply the Preset matching the specified name, if it exists

        """
        if name not in self.presets:
            msg = f'Preset "{name}" does not exist'
            logging.warning(msg)
            return
        self.preset_current = name
        self.apply_preset_data(self.presets[name])

    def apply_preset_data(self, preset: Dict):
        """

        Apply a Preset from data. Themes that appear in the Preset are implicitly enabled. Non-existent Themes need
        to be ignored, etc. If presets are set to merge, then they merge into the existing configuration,
        hence we don't disable those which aren't preset.

        """
        if type(preset) not in {dict, type(None)}:
            msg = f'Received invalid preset. Skipping. {repr(preset)}'
            logging.warning(msg)
            return

        preset = preset or {}
        if (volume := preset.get('volume')) is not None:
            self.set_volume(volume)

        presets_themes = preset.get('themes', {})
        for name, preset in presets_themes.items():
            if name not in self.themes.keys():
                msg = f'Theme "{name}" in has preset but does not exist. Skipping.'
                logging.warning(msg)
                continue
            theme = self.themes[name]
            theme.apply_preset(preset)

        if self.merge_presets:
            return

        for name, theme in self.themes.items():
            if name in presets_themes.keys():
                continue
            theme = self.themes[name]
            theme.enabled = False

    def add_preset(self, name: str):
        """

        Add a new Preset, under the specified name, consisting of the current state

        """
        self.presets[name] = self.get_preset_data()
        self.apply_preset(name)

    def remove_preset(self, name: str):
        """

        Remove the Preset with the specified name.

        """
        if name not in self.presets:
            logging.warning(f'Cannot remove preset "{name}" as it does not exist.')
            return

        self.presets.pop(name)
        logging.warning(f'Removed preset "{name}".')

    def close(self):
        """

        Disable all Themes (and hence close any open Players/Instances on close

        """
        self.enabled = False




class Theme:
    VOLUME_DEFAULT = 40

    def __init__(self, path: Path, device_names: Optional[dict[str, str]] = None):
        """

        Fetch paths from Theme audio directory,and set a default audio output device.

        """

        self.path = path
        self.name = path.stem
        self.paths = self.get_paths()

        if not self.paths:
            msg = f'Theme "{self.name}" directory is empty: "{self.path}"'
            logging.warning(msg)

        self.device_names = device_names or {}
        self._enabled = False

        self.players = None
        self.players_cycle = None
        self.player = None
        self.device_id = None

        self.set_device(device_id=None)

        self.volume_master = 0
        self.volume = self.VOLUME_DEFAULT
        self.volume_scaled = 0
        self.volume_adjust_threshold = 2
        self.set_volume(self.VOLUME_DEFAULT)

    def load_players(self):
        """

        Set up two alternating players (so they can call each other without thread deadlocks)

        """
        if self.players:
            return
        self.players = [self.load_player(), self.load_player()]
        self.players_cycle = cycle(self.players)
        self.switch_player()

    def update_paths(self):
        """

        Update file paths from disk.

        """
        self.paths = self.get_paths()

    def get_dir(self) -> Path:
        """

        Get Theme directory.

        """

        if self.path.is_dir():
            return self.path
        else:
            return self.path.parent

    def get_paths(self) -> list[Path]:
        """

        Get file paths from disk.

        """

        if self.path.is_dir():
            return list(self.path.glob('*'))
        else:
            return [self.path]

    def load_player(self) -> vlc.MediaPlayer:
        """

        Instantiate a new player, and register callbacks

        """
        player = load_new_player()
        player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self.cb_media_player_end_reached)
        msg = f'Theme "{self.name}" loaded new player: {player}'
        logging.debug(msg)
        return player

    def cb_media_player_end_reached(self, event: vlc.Event):
        """

        Method to register as a VLC callback. Once a file finishes playing, start playing the next file in the other player.

        """
        msg = f'Theme "{self.name}" hit media end callback with event: {event.type=}'
        logging.debug(msg)
        self.switch_player()
        self.play()

    @property
    def instance(self) -> vlc.Instance:
        """

        Get the `Instance` behind the current `MediaPlayer`.

        """
        return self.player.get_instance()

    @property
    def device_name(self):
        """

        Get the (friendly) name of the current device. If it doesn't exist, it must have been unplugged etc. so the default needs setting.

        """

        if self.device_id not in self.devices:
            self.set_device(self.device_id)

        return self.devices.get(self.device_id)

    @property
    def devices(self) -> dict[str, str]:
        """

        Create a mapping from audio output device IDs to their friendly names from VLC's peculiar enum format.

        """

        return get_devices(self.player, self.device_names)

    def set_device(self, device_id: Optional[str]):
        """

        Set the output audio device from its ID. Also handle when that device had been unplugged, etc.

        """
        device_id_old = device_id
        devices = self.devices

        device_id = self.get_device_id(device_id)

        if device_id not in devices:
            self.enabled = False
            device_id = next(iter(devices or {None}))
            msg = f'Current device "{device_id_old}" no longer available for theme "{self.name}". ' \
                  f'Defaulting to "{device_id}". Theme will be disabled.'
            logging.warning(msg)

        self.device_id = device_id

        if self.enabled:
            self.player.audio_output_device_set(None, device_id)

    def get_device_id(self, name_or_id: str) -> Optional[str]:
        """

        Get a device ID from its ID (itself) or its friendly name.

        """

        if name_or_id in self.devices:
            return name_or_id

        names_to_ids = {name: id for id, name in self.devices.items()}
        return names_to_ids.get(name_or_id)

    def switch_player(self):
        """

        Alternate the current player.

        """

        self.player = next(self.players_cycle)
        logging.debug(f'Theme "{self.name}" switched player to: {self.player}')

    def play(self):
        """

        Play a single audio file at random from this Theme's directory. Many settings (e.g. the output device) will default between plays,
        so this all needs specifying each time.

        """

        self.load_players()
        path = choice(self.paths)
        media = self.instance.media_new(str(path))
        self.player.set_media(media)
        self.set_device(self.device_id)
        self.player.audio_set_volume(self.volume_scaled)
        logging.info(f'Theme "{self.name}" playing file {path}')
        self.player.play()

    def stop(self):
        """

        When Theme is stopped, unload its players

        """
        for player in self.players or []:
            unload_player(player)
            msg = f'Theme "{self.name}" unloaded player: {player}'
            logging.debug(msg)
        self.players = None
        self.players_cycle = None
        self.player = None

    @property
    def enabled(self) -> bool:
        """

        Is this theme enabled?

        """
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """

        Set whether Theme is enabled. If the input value if different from current, either start playing or toggle pause, depending on Theme state. Themes
        with no tracks (paths) cannot be enabled.

        """

        if not self.paths:
            return

        value = bool(value)
        if value == self._enabled:
            return

        self._enabled = value

        if self._enabled:
            self.play()
        else:
            self.stop()

    def set_volume(self, value: Optional[int] = None):
        """

        Set the scaled volume by multiplying the master volume with the theme volume.

        """

        if value is not None:
            value = sanitize_volume(value)
            self.volume = value

        volume_scaled_old = self.volume_scaled
        volume_scaled = round(self.volume * (self.volume_master / 100))
        logging.info(f'Changing scaled volume for theme "{self.name}": from {volume_scaled_old} to {volume_scaled}')
        self.set_volume_scaled(volume_scaled)

    def set_volume_down(self):
        self.set_volume(self.volume - self.volume_adjust_threshold)

    def set_volume_up(self):
        self.set_volume(self.volume + self.volume_adjust_threshold)

    def set_volume_scaled(self, volume_scaled):
        """

        Set the scaled volume and propagate to player, if enabled

        """
        self.volume_scaled = volume_scaled
        if self.enabled:
            self.player.audio_set_volume(volume_scaled)

    def get_preset(self) -> Dict:
        """

        Get preset data

        """
        return {'volume': self.volume, 'device': self.device_name}

    def apply_preset(self, preset: Dict):
        """

        Apply preset data. Only enabled Themes are mentioned in Presets, so always enable

        """

        logging.info(f'Theme "{self.name}" applying preset: {repr(preset)}')
        if (volume := preset.get('volume')) is not None:
            self.set_volume(volume)

        device = preset.get('device')
        self.set_device(device)

        if self.get_device_id(device):
            self.enabled = True

    @property
    def status(self):
        """

        General Theme status information

        """

        if self.player:
            media = self.player.get_media()
            state = str(self.player.get_state())
            position = self.player.get_position()
        else:
            media = state = position = None

        duration = media.get_duration() if media else None

        if position and duration:
            elapsed = round(position * duration)
        else:
            elapsed = None

        data = {
            'name': self.name,
            'device': {'id': self.device_id, 'name': self.devices.get(self.device_id)},
            'enabled': self.enabled,
            'track_count': len(self.paths),
            'volume': {'theme': self.volume, 'scaled': self.volume_scaled,
                       'adjust_threshold': self.volume_adjust_threshold},
            'position': position,
            'position_percentage': round(position * 100) if position else None,
            'elapsed': elapsed,
            'state': state,
            'duration': media.get_duration() if media else None,
            'meta_data': {
                value: datum
                for key, value in vlc.Meta._enum_names_.items()
                if (datum := media.get_meta(key))
            } if media else None
        }

        return data

    @property
    def status_text(self):
        """

        Brief Theme status overview

        """
        return f'{self.name} @ {self.volume}%'


