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
    name = None
    device = None
    icon_suffix = None

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

    @property
    def uid(self) -> str:
        """

        Unique ID

        """
        return sanitize(self.device.name, self.name, sep='_')

    @property
    def topic_state(self) -> str:
        """

        State topic

        """
        subpath = sanitize(self.device.name, self.name, sep='/')
        topic = f'stat/{subpath}/state'
        return topic

    @property
    def topic_command(self) -> str:
        """

        Command topic

        """
        subpath = sanitize(self.device.name, self.name, sep='/')
        topic = f'stat/{subpath}/command'
        return topic

    @property
    def topic_announce(self) -> str:
        subpath = sanitize(self.device.name, self.name, sep='_')
        topic = f'homeassistant/{self.HA_PLATFORM}/{subpath}/config'

        return topic

    @property
    def icon(self):
        """

        Add Material Design Icons prefix to icon name.

        """
        icon = f"mdi:{self.icon_suffix}" if self.icon_suffix else None
        return icon

    def handle_incoming(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, payload: Any):
        """

        Callback to handle incoming messages.

        """
        raise NotImplementedError()

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce: bool = False):
        """

        Handle outgoing messages, adding announce, subscriptions to the queue.

        """
        if force_announce:
            message = Message(client.publish, self.topic_announce, self.data, serialize=True)
            queue.append(message)
            if self.topic_command:
                message = Message(client.subscribe, self.topic_command)
                queue.append(message)


class Volume(Entity):
    """

    Home Assistant base volume control.

    """
    HA_PLATFORM = 'number'

    def __init__(self, device: Device, name: str, icon: Optional[str] = None, min: Optional[int] = 0, max: Optional[int] = 100):
        self.device = device
        self.name = name
        self.min = min
        self.max = max
        self.icon_suffix = icon
        self.value = None

    @property
    def data(self):
        data = super().data | {
            'min': self.min,
            'max': self.max
        }
        return data


class VolumeMaster(Volume):
    """

    Home Assistant master volume control.

    """
    HA_PLATFORM = 'number'

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'min': self.min,
            'max': self.max
        }
        return data

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        """

        If volume has changed, send update message.

        """
        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)
        value = amniotic.volume
        if value != self.value or force_announce:
            message = Message(client.publish, self.topic_state, value)
            queue.append(message)
            self.value = value

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        """

        Apply change audio volume from incoming message.

        """
        if payload is not None:
            amniotic.set_volume(payload)
        message = Message(client.publish, self.topic_state, amniotic.volume)
        queue.append(message)


class VolumeTheme(Volume):
    """

    Home Assistant theme volume control.

    """

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        """

        If volume has changed, send update message.

        """

        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)
        value = amniotic.theme_current.volume
        if value != self.value or force_announce:
            message = Message(client.publish, self.topic_state, value)
            queue.append(message)
            self.value = value

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        """

        Apply change to audio volume from incoming message.

        """

        if payload is not None:
            amniotic.set_volume_theme(payload)
        message = Message(client.publish, self.topic_state, amniotic.theme_current.volume)
        queue.append(message)


class Select(Entity):
    """

    Base Home Assistant selector.

    """
    HA_PLATFORM = 'select'

    def __init__(
            self,
            device: Device,
            name: str,
            selected=None,
            icon=None,
            options=None,
    ):
        self.device = device
        self.name = name
        self.icon_suffix = icon
        self.options = options or []
        self.selected = selected

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'options': self.options
        }
        return data

    def get_select_state(self, amniotic: Amniotic) -> tuple[list[str], str]:
        """

        Get state of the entity, i.e. the list of options and the currently selected option.

        """
        raise NotImplementedError()

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        """

        Check if the list of options, or the current option, has changed. If so, send the relevant messages. This is a little awkward as if the options have
        changed, the entity needs to be re-announced *before* the current select can be published.

        """

        messages = []
        options, selected_option = self.get_select_state(amniotic)

        if options != self.options:
            force_announce = True
            self.options = options

        if selected_option != self.selected:
            message = Message(client.publish, self.topic_state, selected_option)
            messages.append(message)
            self.selected = selected_option

        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)
        queue += messages


class SelectTheme(Select):
    """

    Home Assistant theme selector.

    """

    def get_select_state(self, amniotic: Amniotic) -> tuple[list[str], str]:
        """

        Get state of the entity, i.e. the list of options and the currently selected option.

        """
        return list(amniotic.themes.keys()), amniotic.theme_current.name

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        """

        Apply change to current Theme from incoming message.

        """
        if payload is not None:
            amniotic.set_theme(payload)
        message = Message(client.publish, self.topic_state, amniotic.theme_current.name)
        queue.append(message)


class SelectDevice(Select):
    """

    Home Assistant device selector.

    """

    def get_select_state(self, amniotic: Amniotic) -> tuple[list[str], str]:
        """

        Get state of the entity, i.e. the list of options and the currently selected option.

        """
        return list(amniotic.devices.values()), amniotic.theme_current.device_name

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        """

        Apply change to current device from incoming message.

        """
        if payload is not None:
            amniotic.theme_current.set_device(payload)
        message = Message(client.publish, self.topic_state, amniotic.theme_current.device_name)
        queue.append(message)


class ToggleTheme(Entity):
    """

    Base Home Assistant Theme enabled/disabled entity (switch/toggle).

    """
    HA_PLATFORM = 'switch'
    VALUE_MAP = [(OFF := 'OFF'), (ON := 'ON')]

    def __init__(self, device: Device, name: str, icon=None):
        self.device = device
        self.name = name
        self.icon_suffix = icon
        self.value = None

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        """

        Apply change to current Theme enabled/disabled from incoming message.

        """
        if payload is not None:
            amniotic.theme_current.enabled = payload == self.ON
        message = Message(client.publish, self.topic_state, self.VALUE_MAP[amniotic.theme_current.enabled])
        queue.append(message)

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        """

        Check if the current Theme enabled/disabled state had changed. If so, send the relevant messages.

        """
        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)

        value = amniotic.theme_current.enabled
        if value != self.value or force_announce:
            message = Message(client.publish, self.topic_state, self.VALUE_MAP[amniotic.theme_current.enabled])
            queue.append(message)
            self.value = value

    @property
    def data(self):
        """

        Home Assistant announce data for the entity.

        """
        data = super().data | {
            'device_class': 'outlet',
        }
        return data