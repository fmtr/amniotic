import json
import logging
import threading
from functools import cached_property
from time import sleep
from typing import Optional, Any

import pip
from johnnydep import JohnnyDist as Package
from paho.mqtt import client as mqtt
from pytubefix import YouTube, Stream

from amniotic.audio import Amniotic
from amniotic.config import NAME
from amniotic.mqtt.device import Device
from amniotic.mqtt.loop import Loop
from amniotic.mqtt.tools import Message, sanitize
from amniotic.version import __version__


class Entity:
    """

    Base representation of an entity for Home Assistant.

    """
    PAYLOAD_ONLINE = "Online"
    PAYLOAD_OFFLINE = "Offline"
    HA_PLATFORM = None
    IS_TELE = False
    NAME = None
    ICON_SUFFIX = None
    VALUE_MAP_ON_OFF = [(OFF := 'OFF'), (ON := 'ON')]
    NA_VALUE = '-'
    value = None

    TEST_ALWAYS_UPDATE = False

    def __init__(self, loop: Loop):
        self.loop = loop

    @property
    def name(self) -> str:
        """

        Home Assistant compatible entity name.

        """

        name = f'{self.device.name} {self.NAME}'
        return name

    @property
    def device(self) -> Device:
        return self.loop.device

    @property
    def queue(self) -> list[Message]:
        return self.loop.queue

    @property
    def client(self) -> mqtt.Client:
        return self.loop.client

    @property
    def amniotic(self) -> Amniotic:
        return self.loop.amniotic

    @property
    def uid(self) -> str:
        """

        Unique ID

        """
        return sanitize(self.name, sep='_')

    @property
    def topic_state(self) -> str:
        """

        State topic

        """
        subpath = sanitize(self.name, sep='/')
        topic = f'stat/{subpath}/state'
        return topic

    @property
    def topic_command(self) -> str:
        """

        Command topic

        """
        subpath = sanitize(self.name, sep='/')
        topic = f'stat/{subpath}/command'
        return topic

    @property
    def topic_announce(self) -> str:
        """

        Topic to announce to Home Assistant

        """
        subpath = sanitize(self.name, sep='_')
        topic = f'homeassistant/{self.HA_PLATFORM}/{subpath}/config'
        return topic

    @property
    def icon(self) -> Optional[str]:
        """

        Add Material Design Icons prefix to icon name.

        """
        if not self.ICON_SUFFIX:
            return self.ICON_SUFFIX

        icon = f"mdi:{self.ICON_SUFFIX}"
        return icon

    @property
    def data(self) -> dict:
        """

        Home Assistant announce data for the entity.

        """
        data = {
            "name": self.name,
            "unique_id": self.uid,
            "object_id": self.uid,
            "device": self.device.announce_data,
            "force_update": True,
            "payload_available": self.PAYLOAD_ONLINE,
            "payload_not_available": self.PAYLOAD_OFFLINE,
            "availability_topic": self.device.topic_lwt,
            "state_topic": self.topic_state,
            "command_topic": self.topic_command,
        }

        if self.icon:
            data['icon'] = self.icon

        return data

    def get_value(self) -> Any:
        raise NotImplementedError()

    def set_value(self, value) -> Any:
        raise NotImplementedError()

    def handle_incoming(self, value: Any):
        """

        Apply change audio volume from incoming message.

        """
        if value is not None:
            self.set_value(value)

    def handle_announce(self):
        message = Message(self.client.publish, self.topic_announce, self.data, serialize=True, is_announce=True)
        self.queue.append(message)
        if self.topic_command:
            message = Message(self.client.subscribe, self.topic_command)
            self.queue.append(message)

    def handle_outgoing(self, force_announce: bool = False):
        """

        Handle outgoing messages, adding announce, subscriptions to the queue.

        """
        if force_announce:
            self.handle_announce()

        value = self.get_value()

        is_tele = (not self.IS_TELE) or self.loop.is_telem_loop
        has_value_changed = value != self.value and is_tele

        if has_value_changed or force_announce:
            self.value = value
            message = Message(self.client.publish, self.topic_state, self.value)
            self.queue.append(message)


class Select(Entity):
    """

    Base Home Assistant selector.

    """
    HA_PLATFORM = 'select'
    ICON_SUFFIX = None
    options: list[str] = []
    selected: Optional[str] = None

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'options': self.options
        }
        return data

    def get_options(self, amniotic: Amniotic) -> list[str]:
        """

        Get state of the entity, i.e. the list of options and the currently selected option.

        """
        raise NotImplementedError()

    def handle_outgoing(self, force_announce: bool = False):
        """

        Handle outgoing messages, adding announce, subscriptions to the queue.

        """

        options = self.get_options(self.amniotic)
        if options != self.options or force_announce:
            force_announce = True
            self.options = options

        super().handle_outgoing(force_announce=force_announce)


class SelectTheme(Select):
    """

    Home Assistant theme selector.

    """
    ICON_SUFFIX = 'surround-sound'
    NAME = 'Theme'

    def get_value(self) -> Any:
        return self.amniotic.theme_current.name

    def set_value(self, value) -> Any:
        self.amniotic.set_theme(value)

    def get_options(self, amniotic: Amniotic) -> list[str]:
        """

        Ensure Themes are up-to-date with what's on disk, and return a list of their names

        """
        self.amniotic.load_themes()
        return sorted(amniotic.themes.keys())


class Volume(Entity):
    """

    Home Assistant base volume control.

    """
    HA_PLATFORM = 'number'
    MIN = 0
    MAX = 100

    @property
    def data(self):
        data = super().data | {
            'min': self.MIN,
            'max': self.MAX
        }
        return data


class VolumeMaster(Volume):
    """

    Home Assistant master volume control.

    """
    ICON_SUFFIX = 'volume-high'
    NAME = 'Master Volume'

    def get_value(self) -> Any:
        return self.amniotic.volume

    def set_value(self, value) -> Any:
        self.amniotic.set_volume(value)


class VolumeAdjustThreshold(Volume):
    """

    Home Assistant volume adjust threshold control.

    """
    ICON_SUFFIX = 'volume-equal'
    NAME = 'Master Volume Adjust Threshold'
    MIN = 1
    MAX = 10

    def get_value(self) -> Any:
        return self.amniotic.volume_adjust_threshold

    def set_value(self, value) -> Any:
        self.amniotic.set_volume_adjust_threshold(value)


class VolumeTheme(Volume):
    """

    Home Assistant theme volume control.

    """

    ICON_SUFFIX = 'volume-medium'
    NAME = 'Theme Volume'

    def get_value(self) -> Any:
        return self.amniotic.theme_current.volume

    def set_value(self, value) -> Any:
        self.amniotic.set_volume_theme(value)


class DeviceTheme(Select):
    """

    Home Assistant device selector.

    """
    ICON_SUFFIX = 'expansion-card-variant'
    NAME = 'Theme Device'

    def get_value(self) -> Any:
        return self.amniotic.theme_current.device_name

    def set_value(self, value) -> Any:
        self.amniotic.theme_current.set_device(value)

    def get_options(self, amniotic: Amniotic) -> list[str]:
        """

        Get state of the entity, i.e. the list of options and the currently selected option.

        """
        return list(amniotic.devices.values())


class Toggle(Entity):
    """

    Base Home Assistant toggle entity.

    """
    HA_PLATFORM = 'switch'

    def get_value(self) -> Any:
        return self.VALUE_MAP_ON_OFF[self.amniotic.theme_current.enabled]

    def set_value(self, value) -> Any:
        self.amniotic.theme_current.enabled = value == self.ON


class ToggleTheme(Toggle):
    """

    Home Assistant Theme enabled/disabled entity (switch/toggle).

    """
    ICON_SUFFIX = 'play-circle'
    NAME = 'Theme Enabled'

    def get_value(self) -> Any:
        return self.VALUE_MAP_ON_OFF[self.amniotic.theme_current.enabled]

    def set_value(self, value) -> Any:
        self.amniotic.theme_current.enabled = value == self.ON


class ToggleMergePresets(Toggle):
    """

    Base Home Assistant Presets Merge enabled/disabled entity.

    """
    ICON_SUFFIX = 'set-merge'
    NAME = 'Merge Presets'

    def get_value(self) -> Any:
        return self.VALUE_MAP_ON_OFF[self.amniotic.merge_presets]

    def set_value(self, value) -> Any:
        self.amniotic.merge_presets = value == self.ON


class Button(Entity):
    """

    Home Assistant button

    """
    HA_PLATFORM = 'button'

    def get_value(self) -> Any:
        pass

    def set_value(self, value) -> Any:
        pass


class ButtonDisableAllThemes(Button):
    """

    Home Assistant button to disable all Themes

    """
    NAME = 'Disable All Themes'
    ICON_SUFFIX = 'stop-circle'

    def handle_incoming(self, value: Any):
        """

        Disable all themes

        """
        self.amniotic.enabled = False


class ButtonVolumeDownMaster(Button):
    NAME = 'Master Volume Down'
    ICON_SUFFIX = 'volume-minus'

    def handle_incoming(self, value: Any):
        """

        Decrement volume

        """
        self.amniotic.set_volume_down()


class ButtonVolumeUpMaster(Button):
    NAME = 'Master Volume Up'
    ICON_SUFFIX = 'volume-plus'

    def handle_incoming(self, value: Any):
        """

        Increment volume

        """
        self.amniotic.set_volume_up()


class ButtonVolumeDownTheme(Button):
    NAME = 'Theme Volume Down'
    ICON_SUFFIX = 'volume-minus'

    def handle_incoming(self, value: Any):
        """

        Decrement volume

        """
        self.amniotic.theme_current.set_volume_down()


class ButtonVolumeUpTheme(Button):
    NAME = 'Theme Volume Up'
    ICON_SUFFIX = 'volume-plus'

    def handle_incoming(self, value: Any):
        """

        Increment volume

        """
        self.amniotic.theme_current.set_volume_up()


class ButtonRestart(Button):
    NAME = 'Restart'
    ICON_SUFFIX = 'restart-alert'

    def handle_incoming(self, value: Any):
        """

        Tell Loop to end

        """
        self.loop.exit_reason = 'Restart requested'


class ButtonUpdateCheck(Button):
    """

    Home Assistant update button.

    """

    ICON_SUFFIX = 'source-branch-sync'
    NAME = 'Update Check'

    @cached_property
    def update_sensor(self):
        """

        Get the sensor for displaying update messages

        """
        from amniotic.mqtt.sensor import UpdateStatus
        update_status = self.loop.entities[UpdateStatus]
        return update_status

    def get_pypi_latest(self) -> Optional[str]:
        """

        Check if newer version is available.

        """
        package = Package(NAME)
        version = package.version_latest
        if __version__ == package.version_latest:
            return None
        else:
            return version

    def check_update(self):
        """

        Report newer version, if one exists, using update sensor

        """

        try:
            version = self.get_pypi_latest()
        except Exception as exception:
            self.update_sensor.message = f'Error checking for updates ({exception.__class__.__name__})'
            return

        if version:
            message = f'Update available: {version}'
        else:
            message = 'None available'
        self.update_sensor.message = message

    def handle_incoming(self, value: Any):
        """

        When button is pressed, call update method without blocking.

        """

        self.update_sensor.message = 'Checking for updates...'
        threading.Thread(target=self.check_update).start()


class ButtonUpdate(ButtonUpdateCheck):
    """

    Home Assistant update button.

    """

    HA_PLATFORM = 'button'
    NAME = 'Update'
    ICON_SUFFIX = None

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """

        data = super().data | {
            'device_class': 'update'
        }

        return data

    def do_update(self):
        """

        Update from PyPI, then tell loop to exit.

        """

        try:
            pip.main(['install', NAME, '--upgrade'])
        except:
            self.update_sensor.message = 'Error updating'
            return
        self.update_sensor.message = 'Update complete. Restarting...'
        sleep(self.loop.DELAY_FIRST)
        self.loop.exit_reason = f'Updating to latest version.'

    def handle_incoming(self, value: Any):
        """

        When button is pressed, call update method without blocking.

        """

        self.update_sensor.message = 'Updating...'
        threading.Thread(target=self.do_update).start()


class TextInput(Entity):
    """

    Base Home Assistant text input box.

    """
    HA_PLATFORM = 'text'
    status = ""

    @cached_property
    def update_sensor(self):
        """

        Get the sensor for displaying update messages

        """
        raise NotImplementedError()

    def set_value(self, value) -> Any:
        """

        Dummy method

        """
        pass

    def get_value(self) -> Any:
        """

        The current state of this control.

        """
        return self.status

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'mode': 'text',
        }
        return data


class NewTheme(TextInput):
    """

    Home Assistant text input box for creating a new Theme

    """
    ICON_SUFFIX = 'folder-plus-outline'
    NAME = 'Create New Theme'

    def handle_incoming(self, value: Any):
        """

        Add specified theme and set to current

        """
        self.amniotic.add_new_theme(value, set_current=True)


class Downloader(TextInput):
    """

    Home Assistant track downloader URL input.

    """
    ICON_SUFFIX = 'cloud-download-outline'
    NAME = 'Download YouTube Link'
    DOWNLOADING = 'Starting...'
    IDLE = ''

    @cached_property
    def update_sensor(self):
        """

        Get the sensor for displaying update messages

        """
        from amniotic.mqtt.sensor import DownloadStatus
        update_status = self.loop.entities[DownloadStatus]
        return update_status

    def progress_callback(self, stream: Stream, chunk: bytes, bytes_remaining: int):
        """

        Send download progress to sensor

        """

        percentage = (1 - (bytes_remaining / stream.filesize)) * 100
        self.update_sensor.message = f'Downloading: {round(percentage)}% complete'

    def completed_callback(self, stream: Stream, path: str):
        """

        Send download completion message to sensor

        """

        self.update_sensor.message = f'Download complete: "{stream.title}"'
        self.status = self.IDLE

    def do_download(self, url: str):
        """

        Download highest bitrate audio stream from the video specified. Log any errors/progress to the relevant sensor

        """

        try:
            self.status = self.DOWNLOADING
            theme = self.amniotic.theme_current
            self.update_sensor.message = 'Fetching video metadata...'

            video = YouTube(
                url,
                on_progress_callback=self.progress_callback,
                on_complete_callback=self.completed_callback
            )
            self.update_sensor.message = 'Finding audio streams...'
            audio_streams = video.streams.filter(only_audio=True).order_by('bitrate')
            if not audio_streams:
                self.update_sensor.message = f'Error downloading: no audio streams found in "{video.title}"'
                self.status = self.IDLE
                return
            stream = audio_streams.last()

            if stream.filesize == 0:
                self.update_sensor.message = f'Error downloading: empty audio stream found in "{video.title}"'
                self.status = self.IDLE
                return

            self.update_sensor.message = 'Starting download...'
            stream.download(output_path=str(theme.get_dir()))

        except Exception as exception:

            self.update_sensor.message = f'Error downloading: {exception.__class__.__name__}'
            logging.error(f'Download error for "{url}": {repr(exception)}')
            self.status = self.IDLE
            return

    def handle_incoming(self, value: Any):
        """

        Start download from the specified URL without blocking.

        """

        if self.status == self.DOWNLOADING:
            return
        threading.Thread(target=self.do_download, args=[value]).start()


class PresetData(TextInput):
    """

    Home Assistant text input box for I/O of Presets

    """
    ICON_SUFFIX = 'cog-play'
    NAME = 'Preset Data'

    def update_sensor(self):
        pass

    def set_value(self, value) -> Any:
        """

        Apply preset data

        """
        self.amniotic.apply_preset_data(value)

    def get_value(self) -> str:
        """

        Current settings as Preset data

        """
        preset = self.amniotic.get_preset_data()
        preset_json = json.dumps(preset)
        return preset_json


class SaveDeletePreset(TextInput):
    """

    Home Assistant base text input box for saving/deleting Presets

    """
    PATTERN = '^[^\.].*$'

    def update_sensor(self):
        pass

    @property
    def data(self):
        """

        Home Assistant announce data for the entity. Don't allow Preset names to start with a '.' because these will be
        used internally as special cases (e.g. last-used Preset)

        """
        data = super().data | {
            # 'pattern': self.PATTERN TODO: Fix this
        }
        return data

    def get_value(self) -> Optional[str]:
        """

        We can leave the text as the last value the user entered, so no need to return anything here

        """
        return None

    def write_presets(self) -> int:
        """

        Write out presets after change

        """
        return self.loop.config.write_presets(
            presets=self.amniotic.presets,
            preset_last=self.amniotic.get_preset_data()
        )


class SavePreset(SaveDeletePreset):
    """

    Home Assistant text input box for naming/saving a new Preset

    """
    ICON_SUFFIX = 'content-save-plus'
    NAME = 'Save Preset As'

    def set_value(self, value):
        """

        Add a new Preset

        """
        self.amniotic.add_preset(value)
        self.write_presets()


class DeletePreset(SaveDeletePreset):
    """

    Home Assistant text input box for deleting Preset

    """
    ICON_SUFFIX = 'trash-can'
    NAME = 'Delete Preset'
    PATTERN = '^[^\.].*$'  # TODO: Inherit this (and data/update_sensor) from common "PresetIO".

    def update_sensor(self):
        pass

    def set_value(self, value):
        """

        Remove a Preset

        """
        self.amniotic.remove_preset(value)
        self.write_presets()


class Preset(Select):
    """

    Home Assistant Presets selector.

    """
    ICON_SUFFIX = 'window-shutter-cog'
    NAME = 'Preset'
    NA_VALUE = ""

    def get_value(self) -> str:
        """

        Get the currently selected Preset, if there is one

        """
        return self.amniotic.get_preset() or self.NA_VALUE

    def set_value(self, value) -> str:
        """

        If selector isn't empty, apply the selected Preset

        """
        if value == self.NA_VALUE:
            return
        self.amniotic.apply_preset(value)

    def get_options(self, amniotic: Amniotic) -> list[str]:
        """

        Get state of the entity, i.e. the list of options and the currently selected option. Also allow no entry to
        be selected

        """
        return [self.NA_VALUE] + sorted(amniotic.presets.keys())
