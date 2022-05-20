import getpass
import logging
from datetime import datetime
from itertools import cycle
from pathlib import Path
from random import choice
from typing import Union, Optional

import vlc

VLC_VERBOSITY = 0


class Amniotic:
    VOLUME_DEFAULT = 50

    def __init__(self, path_base: Union[Path, str], device_names: Optional[dict[str, str]] = None):
        """

        Read audio directories and instantiate Channel objects

        """

        user = getpass.getuser()
        if user == 'root':
            msg = f'You are running as root. This could cause issues with PulseAudio, unless it is configured in system-wide mode.'
            logging.warning(msg)

        self.device_names = device_names or {}
        self._enabled = True
        path_base = Path(path_base).absolute()
        paths_channels = sorted([path.absolute() for path in path_base.glob('*') if path.is_dir()])

        if not paths_channels:
            msg = f'No audio directories found in "{path_base}"'
            raise FileNotFoundError(msg)

        self.channels = [Channel(path, device_names=self.device_names) for path in paths_channels]
        self.channel_current = self.channels[0]
        self.channels = {channel.name: channel for channel in self.channels}
        self.volume = 0
        self.set_volume(self.VOLUME_DEFAULT)

    @property
    def devices(self) -> dict[str, str]:
        """

        Get general (system-wide) devices. Just use those of the first Channel.

        """
        return self.channel_current.devices

    @property
    def enabled(self) -> bool:
        """

        Are any Channels enabled?

        """
        return any([channel.enabled for channel in self.channels.values()])

    @enabled.setter
    def enabled(self, value: bool):
        """

        If set to `False`, disable all Channels.

        """
        value = bool(value)
        self._enabled = value

        if not self._enabled:
            for channel in self.channels.values():
                channel.enabled = self._enabled

    def set_channel(self, id: str):
        """

        Set current channel by the specified name/ID.

        """
        if id not in self.channels:
            id = self.channel_current.get_device_id(id)
        self.channel_current = self.channels[id]

    def set_volume(self, value: int):
        """

        Set Master Volume, and propagate to all Channels.

        """
        self.volume = value
        for channel in self.channels.values():
            channel.set_volume(self.volume)

    def set_volume_channel(self, value):
        """

        Set the current Channel Volume.

        """
        self.channel_current.set_volume(self.volume, value)

    @property
    def status(self) -> dict:
        """

        General status information, including that of all channels.

        """
        channels = [channel.status for channel in self.channels.values()]
        data = {'datetime': datetime.now().isoformat(), 'volume': self.volume, 'channels': channels}
        return data


class Channel:
    VOLUME_DEFAULT = 40

    def __init__(self, path: Path, device_names: Optional[dict[str, str]] = None):
        """

        Fetch paths from Channel audio directory, set up two alternating players (so they can call each other without thread deadlocks) and set a default
        audio output device.

        """
        self.path = path
        self.name = path.stem
        self.paths = list(path.glob('*'))
        if not self.paths:
            msg = f'Audio directory is empty: "{path}"'
            raise FileNotFoundError(msg)

        self.device_names = device_names or {}
        self._enabled = False
        self.ever_started = False

        self.players = cycle([self.get_player(), self.get_player()])
        self.player = self.device = None
        self.switch_player()
        self.set_device(device=None)
        self.volume = self.VOLUME_DEFAULT
        self.volume_scaled = self.volume

    def get_player(self) -> vlc.MediaPlayer:
        instance = vlc.Instance(f'--verbose {VLC_VERBOSITY}')
        player = vlc.MediaPlayer(instance)
        player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self.cb_media_player_end_reached)
        return player

    def cb_media_player_end_reached(self, event: vlc.Event):
        """

        Method to register as a VLC callback. Once a file finishes playing, start playing the next file in the other player.

        """
        logging.debug(f'Channel "{self.name}" hit media end callback with event: {event.type=} {event.obj=} {event.meta_type=}')
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

        devices_raw = self.player.audio_output_device_enum()
        devices = {}
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
                devices[device] = self.device_names.get(description, description)
                device_raw = device_raw.next

        return devices

    def set_device(self, device: str):
        """

        Set the output audio device from its ID. Also handle when that device had been unplugged, etc.

        """
        devices = self.devices

        if device not in devices:
            device = self.get_device_id(device)

        if device not in devices:
            self.enabled = False
            device = next(iter(devices or {None}))
            msg = f'Current device "{self.device}" no longer available for channel "{self.name}". ' \
                  f'Defaulting to "{device}". Channel will be disabled.'
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
        self.player = next(self.players)
        logging.debug(f'Channel "{self.name}" switched player to: {self.player}')

    def play(self):
        """

        Play a single audio file at random from this Channel's directory. Many settings (e.g. the output device) will default between plays,
        so this all needs specifying each time.

        """
        self.ever_started = True
        path = choice(self.paths)
        media = self.instance.media_new(str(path))
        self.player.set_media(media)
        self.set_device(self.device)
        self.player.audio_set_volume(self.volume_scaled)
        logging.info(f'Channel "{self.name}" playing file {path}')
        self.player.play()

    @property
    def enabled(self) -> bool:
        """

        Is this channel enabled?

        """
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """

        Set whether Channel is enabled. If the input value if different from current, either start playing or toggle pause, depending on Channel state.

        """
        value = bool(value)
        if value == self._enabled:
            return

        self._enabled = value

        if not self.ever_started and self._enabled:
            self.play()
        else:
            self.player.pause()

    def set_volume(self, volume_master: int, volume: Optional[int] = None):
        """

        Set the scaled volume by multiplying the master volume with the channel volume.

        """

        if volume is not None:
            self.volume = volume

        volume_old = self.volume_scaled
        volume_scaled = round(self.volume * (volume_master / 100))
        logging.info(f'Changing scaled volume for channel "{self.name}": from {volume_old} to {volume_scaled}')
        self.volume_scaled = volume_scaled
        self.player.audio_set_volume(volume_scaled)

    @property
    def status(self):
        """

        General Channel status information

        """
        media = self.player.get_media()

        data = {
            'name': self.name,
            'device': {'id': self.device, 'name': self.devices[self.device]},
            'enabled': self.enabled,
            'volume': {'channel': self.volume, 'scaled': self.volume_scaled},
            'position': self.player.get_position(),
            'state': str(self.player.get_state()),
            'duration': media.get_duration() if media else None,
            'duration_percentage': round(media.get_duration() * 100) if media else None,
            'meta_data': {
                value: datum
                for key, value in vlc.Meta._enum_names_.items()
                if (datum := media.get_meta(key))
            } if media else None
        }

        return data
