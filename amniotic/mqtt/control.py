from typing import Optional, Any

from paho.mqtt import client as mqtt

from amniotic.audio import Amniotic
from amniotic.config import MAC_ADDRESS
from amniotic.mqtt.tools import Message, sanitize
from amniotic.version import __version__


class Device:
    """

    Representation of the parent device for Home Assistant.

    """
    NAME = 'Amniotic'
    MODEL = 'Amniotic'
    MANUFACTURER = 'Frontmatter'
    URL = None

    def __init__(self, location: Optional[str] = None):
        """

        Set any specified arguments.

        """
        self.location = location

    @property
    def uid(self) -> str:
        """

        Home Assistant compatible unique ID.

        """
        uid = sanitize(self.name, MAC_ADDRESS)
        return uid

    @property
    def name(self) -> str:
        """

        Home Assistant compatible device name.

        """

        name = self.NAME
        if self.location:
            name = f'{self.location} {name}'

        return name

    @property
    def topic_lwt(self) -> str:
        """

        Device LWT path.

        """
        subpath = sanitize(self.name, sep='/')
        topic = f'tele/{subpath}/LWT'
        return topic

    @property
    def announce_data(self) -> dict:
        """

        Home Assistant announce data for the device.

        """
        data = {
            "connections": [["mac", self.uid]],
            'sw_version': __version__,
            'name': self.name,
            'model': self.MODEL,
            'manufacturer': self.MANUFACTURER,
            'identifiers': self.uid
        }
        return data


class Entity:
    """

    Base representation of an entity for Home Assistant.

    """
    PAYLOAD_ONLINE = "Online"
    PAYLOAD_OFFLINE = "Offline"
    HA_PLATFORM = None
    NAME = None
    ICON_SUFFIX = None
    value = None

    def __init__(self, loop: 'AmnioticMqttEventLoop'):
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
    def icon(self):
        """

        Add Material Design Icons prefix to icon name.

        """
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
            "device_class": self.HA_PLATFORM,
            "force_update": True,
            "payload_available": self.PAYLOAD_ONLINE,
            "payload_not_available": self.PAYLOAD_OFFLINE,
            "availability_topic": self.device.topic_lwt,
            "state_topic": self.topic_state,
            "command_topic": self.topic_command,
            "icon": self.icon
        }
        return data

    def get_value(self) -> Any:
        raise NotImplementedError()

    def set_value(self, value) -> Any:
        raise NotImplementedError()

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, value: Any):
        """

        Apply change audio volume from incoming message.

        """
        if value is not None:
            self.set_value(value)
        message = Message(client.publish, self.topic_state, self.get_value())
        queue.append(message)

    def handle_announce(self, client: mqtt.Client, queue: list[Message], ):
        message = Message(client.publish, self.topic_announce, self.data, serialize=True)
        queue.append(message)
        if self.topic_command:
            message = Message(client.subscribe, self.topic_command)
            queue.append(message)

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce: bool = False):
        """

        Handle outgoing messages, adding announce, subscriptions to the queue.

        """
        if force_announce:
            self.handle_announce(client, queue)

        value = self.get_value()
        if value != self.value or force_announce:
            self.set_value(value)
            self.value = self.get_value()
            message = Message(client.publish, self.topic_state, self.value)
            queue.append(message)



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

    def get_value(self) -> Any:
        raise NotImplementedError()

    def set_value(self, value) -> Any:
        raise NotImplementedError()

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce: bool = False):
        """

        Handle outgoing messages, adding announce, subscriptions to the queue.

        """

        options = self.get_options(amniotic)
        if options != self.options or force_announce:
            force_announce = True
            self.options = options

        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)



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

        Get state of the entity, i.e. the list of options and the currently selected option.

        """
        return list(amniotic.themes.keys())


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
    HA_PLATFORM = 'number'
    ICON_SUFFIX = 'volume-high'
    NAME = 'Master Volume'

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'min': self.MIN,
            'max': self.MAX
        }
        return data

    def get_value(self) -> Any:
        return self.amniotic.volume

    def set_value(self, value) -> Any:
        self.amniotic.set_volume(value)






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





class ToggleTheme(Entity):
    """

    Base Home Assistant Theme enabled/disabled entity (switch/toggle).

    """
    HA_PLATFORM = 'switch'
    ICON_SUFFIX = 'play-circle'
    VALUE_MAP = [(OFF := 'OFF'), (ON := 'ON')]
    NAME = 'Theme Enabled'

    def get_value(self) -> Any:
        return self.VALUE_MAP[self.amniotic.theme_current.enabled]

    def set_value(self, value) -> Any:
        self.amniotic.theme_current.enabled = value == self.ON

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'device_class': 'outlet',
        }
        return data
