import getpass
import logging
import vlc
from cachetools.func import ttl_cache
from datetime import datetime
from itertools import cycle
from pathlib import Path
from random import choice
from typing import Union, Optional

VLC_VERBOSITY = 0
DEVICES_POLL_PERIOD_SECONDS = 10

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
    unload_player(player)
    logging.info(f'Unloading temporary player.')
    return devices_raw

def get_devices(player: Optional[vlc.MediaPlayer] = None, device_names: dict[str, str] = None) -> dict[str, str]:
    """

    Create a mapping from audio output device IDs to their friendly names from VLC's peculiar enum format.

    """

    if player:
        devices_raw = player.audio_output_device_enum()
    else:
        devices_raw = get_devices_raw()

    devices = {}
    device_names = device_names or {}
    if devices_raw:
        device_raw = devices_raw
        count = 0
        while device_raw:
            count += 1
            device_raw = device_raw.contents
            description = device_raw.description.decode()
            device = device_raw.device.decode()
            count = len([key for key in devices.keys() if key == description])
            if count:
                description = f'{description} ({count + 1})'
            devices[device] = device_names.get(description, description)
            device_raw = device_raw.next

    return devices


class Amniotic:
    VOLUME_DEFAULT = 50
    THEME_NAME_DEFAULT = 'Default Theme'

    def __init__(self, path: Union[Path, str], device_names: Optional[dict[str, str]] = None):
        """

        Read audio directories and instantiate Theme objects

        """


        user = getpass.getuser()
        if user == 'root':
            msg = f'You are running as root. This could cause issues with PulseAudio, unless it is configured in system-wide mode.'
            logging.warning(msg)

        self.device_names = device_names or {}
        self._enabled = True
        path = Path(path).absolute()
        paths_themes = sorted([path.absolute() for path in path.glob('*') if path.is_dir()])

        if not paths_themes:
            msg = f'No audio directories found in "{path}". Default theme will be created.'
            logging.warning(msg)

        self.path = path

        self.themes = [Theme(path, device_names=self.device_names) for path in paths_themes]
        self.themes = {theme.name: theme for theme in self.themes}
        if not self.themes:
            self.add_new_theme(self.THEME_NAME_DEFAULT)

        self.theme_current = None
        self.set_theme(next(iter(self.themes.keys())))

        self.volume_adjust_threshold = 2
        self.volume = 0
        self.set_volume(self.VOLUME_DEFAULT)

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
        value = min(value, 100)
        value = max(value, 0)
        self.volume = value
        for theme in self.themes.values():
            theme.set_volume(self.volume)

    def set_volume_adjust_threshold(self, value: int):
        self.volume_adjust_threshold = value

    def set_volume_down(self):
        self.set_volume(self.volume - self.volume_adjust_threshold)

    def set_volume_up(self):
        self.set_volume(self.volume + self.volume_adjust_threshold)

    def set_volume_theme(self, value):
        """

        Set the current Theme Volume.

        """
        self.theme_current.set_volume(self.volume, value)

    @property
    def status(self) -> dict:
        """

        General status information, including that of all themes.

        """
        themes = [theme.status for theme in self.themes.values()]
        data = {'datetime': datetime.now().isoformat(), 'volume': self.volume, 'themes': themes}
        return data


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
        self.device = None

        self.set_device(device=None)
        self.volume = self.VOLUME_DEFAULT
        self.volume_scaled = self.volume

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

    def get_paths(self) -> list[Path]:
        """

        Get file paths from disk.

        """
        paths = list(self.path.glob('*'))

        return paths

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
        msg = f'Theme "{self.name}" hit media end callback with event: {event.type=} {event.obj=} {event.meta_type=}'
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

        if self.device not in self.devices:
            self.set_device(self.device)

        return self.devices.get(self.device)

    @property
    def devices(self) -> dict[str, str]:
        """

        Create a mapping from audio output device IDs to their friendly names from VLC's peculiar enum format.

        """

        return get_devices(self.player, self.device_names)

    def set_device(self, device: Optional[str]):
        """

        Set the output audio device from its ID. Also handle when that device had been unplugged, etc.

        """
        devices = self.devices

        if device not in devices:
            device = self.get_device_id(device)

        if device not in devices:
            self.enabled = False
            device = next(iter(devices or {None}))
            msg = f'Current device "{self.device}" no longer available for theme "{self.name}". ' \
                  f'Defaulting to "{device}". Theme will be disabled.'
            logging.warning(msg)

        self.device = device

        if self.enabled:
            self.player.audio_output_device_set(None, device)

    def get_device_id(self, name: str) -> Optional[str]:
        """

        Get a device ID from its friendly name.

        """
        device_id = {name: id for id, name in self.devices.items()}.get(name)
        return device_id

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
        self.set_device(self.device)
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

    def set_volume(self, volume_master: int, volume: Optional[int] = None):
        """

        Set the scaled volume by multiplying the master volume with the theme volume.

        """

        if volume is not None:
            self.volume = volume

        volume_old = self.volume_scaled
        volume_scaled = round(self.volume * (volume_master / 100))
        logging.info(f'Changing scaled volume for theme "{self.name}": from {volume_old} to {volume_scaled}')
        self.volume_scaled = volume_scaled
        if self.enabled:
            self.player.audio_set_volume(volume_scaled)

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
            'device': {'id': self.device, 'name': self.devices.get(self.device)},
            'enabled': self.enabled,
            'track_count': len(self.paths),
            'volume': {'theme': self.volume, 'scaled': self.volume_scaled},
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
