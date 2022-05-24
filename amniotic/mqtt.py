from json import JSONDecodeError

import json
import logging
import paho.mqtt.client as mqtt
from _socket import gethostname
from dataclasses import dataclass
from datetime import timedelta
from getmac import getmac
from time import sleep
from typing import Any, Callable, Optional, Union

from amniotic.audio import Amniotic
from amniotic.config import Config
from amniotic.version import __version__

MAC_ADDRESS = getmac.get_mac_address().replace(':', '')
HOSTNAME = gethostname()


@dataclass
class Message:
    """

    Object representing an MQTT message.

    """
    method: Callable
    topic: str
    data: Any = None
    serialize: bool = False

    def __post_init__(self):
        """

        If data requires JSON serialization, apply it.

        """
        if self.serialize:
            self.data = json.dumps(self.data)

    def __str__(self):
        """

        String representation from logging etc.

        """
        return f'{self.method.__name__}:{self.topic}>{self.data}'

    def send(self):
        """

        Send the message by applying the method to the data.

        """
        args = [] if self.data is None else [self.data]
        self.method(self.topic, *args, qos=1)


def sanitize(string, sep='-') -> str:
    """

    Replace spaces with URL- and ID-friendly characters, etc.

    """
    return string.lower().strip().replace(' ', sep)


class AmnioticHomeAssistantMqttDevice:
    """

    Representation of the parent device for Home Assistant.

    """
    NAME_DEFAULT = 'Amniotic'
    MODEL_DEFAULT = 'Amniotic'
    MANUFACTURER = 'Frontmatter'
    URL = None

    def __init__(self, name: Optional[str] = None, location: Optional[str] = None):
        """

        Set any specified arguments.

        """
        self.sw_version = __version__
        self._name = name or self.NAME_DEFAULT
        self.location = location

    @property
    def uid(self) -> str:
        """

        Home Assistant compatible unique ID.

        """
        return sanitize(f'{self.location or ""} {self.name} {MAC_ADDRESS}')

    @property
    def name(self) -> str:
        """

        Home Assistant compatible device name.

        """
        return f'{self.location or ""} {self._name}'.strip()

    @property
    def topic_lwt(self) -> str:
        """

        Device LWT path.

        """
        subpath = sanitize(f'{self.location or ""} {self._name}'.strip(), sep='/')
        return f'tele/{subpath}/LWT'

    @property
    def announce_data(self) -> dict:
        """

        Home Assistant announce data for the device.

        """
        data = {
            "connections": [["mac", MAC_ADDRESS]],
            'sw_version': self.sw_version,
            'name': self.name,
            'model': self.MODEL_DEFAULT,
            'manufacturer': self.MANUFACTURER,
            'identifiers': self.uid
        }
        return data


class AmnioticHomeAssistantMqttEntity:
    """

    Base representation of an entity for Home Assistant.

    """
    PAYLOAD_ONLINE = "Online"
    PAYLOAD_OFFLINE = "Offline"
    HA_PLATFORM = None
    name = None
    device = None
    _icon = None

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
    def uid(self):
        return sanitize(f'{self.device.name} {self.name}', sep='_')

    @property
    def topic_state(self):
        subpath = sanitize(f'{self.device.name} {self.name}', sep='/')
        return f'stat/{subpath}/state'

    @property
    def topic_command(self):
        subpath = sanitize(f'{self.device.name} {self.name}', sep='/')
        return f'stat/{subpath}/command'

    @property
    def topic_announce(self):
        subpath = sanitize(f'{self.device.name} {self.name}', sep='-')
        path = f'homeassistant/{self.HA_PLATFORM}/{subpath}/config'

        return path

    @property
    def icon(self):
        """

        Add Material Design Icons prefix to icon name.

        """
        icon = f"mdi:{self._icon}" if self._icon else None
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


class AmnioticHomeAssistantMqttVolume(AmnioticHomeAssistantMqttEntity):
    """

    Home Assistant base volume control.

    """
    HA_PLATFORM = 'number'

    def __init__(self, device: AmnioticHomeAssistantMqttDevice, name: str, icon: Optional[str] = None, min: Optional[int] = 0, max: Optional[int] = 100):
        self.device = device
        self.name = name
        self.min = min
        self.max = max
        self._icon = icon
        self.value = None

    @property
    def data(self):
        data = super().data | {
            'min': self.min,
            'max': self.max
        }
        return data


class AmnioticHomeAssistantMqttVolumeMaster(AmnioticHomeAssistantMqttVolume):
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


class AmnioticHomeAssistantMqttVolumeTheme(AmnioticHomeAssistantMqttVolume):
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


class AmnioticHomeAssistantMqttSelect(AmnioticHomeAssistantMqttEntity):
    """

    Base Home Assistant selector.

    """
    HA_PLATFORM = 'select'

    def __init__(
            self,
            device: AmnioticHomeAssistantMqttDevice,
            name: str,
            selected=None,
            icon=None,
            options=None,
    ):
        self.device = device
        self.name = name
        self._icon = icon
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


class AmnioticHomeAssistantMqttSelectTheme(AmnioticHomeAssistantMqttSelect):
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


class AmnioticHomeAssistantMqttSelectDevice(AmnioticHomeAssistantMqttSelect):
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


class AmnioticHomeAssistantMqttEnabled(AmnioticHomeAssistantMqttEntity):
    """

    Base Home Assistant Theme enabled/disabled entity (switch/toggle).

    """
    HA_PLATFORM = 'switch'
    VALUE_MAP = [(OFF := 'OFF'), (ON := 'ON')]

    def __init__(self, device: AmnioticHomeAssistantMqttDevice, name: str, icon=None):
        self.device = device
        self.name = name
        self._icon = icon
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


class AmnioticHomeAssistantMqttSensor(AmnioticHomeAssistantMqttEntity):
    """

    Base Home Assistant Theme sensor entity, sends messages taken from current Theme status data.

    """
    HA_PLATFORM = 'sensor'
    NA_VALUE = '-'
    META_KEY = None
    IS_SOURCE_META = True
    UOM = None

    def __init__(self, device: AmnioticHomeAssistantMqttDevice, name: str, icon: Optional[str] = None):
        self.device = device
        self.name = name
        self._icon = icon
        self.value = None

    @property
    def topic_command(self):
        return None

    @property
    def data(self):
        data = super().data
        data.pop('device_class')
        if self.UOM:
            data['unit_of_measurement'] = self.UOM
        return data

    def get_value(self, amniotic: Amniotic, key: Optional[str] = None) -> Union[str, int, float]:
        """

        Get the relevant value from the Theme status or metadata dictionaries

        """
        key = key or self.META_KEY
        status = amniotic.theme_current.status
        if self.IS_SOURCE_META:
            status = status.get('meta_data') or {}
        meta_value = status.get(key) or self.NA_VALUE
        return meta_value

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        """

        Check if the current value as changed. If so, send the relevant messages.

        """

        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)

        value = self.get_value(amniotic)
        if value != self.value:
            self.value = value
            message = Message(client.publish, self.topic_state, self.value)
            queue.append(message)


class AmnioticHomeAssistantMqttSensorTitle(AmnioticHomeAssistantMqttSensor):
    """

    Home Assistant Title sensor

    """
    META_KEY = 'Title'


class AmnioticHomeAssistantMqttSensorAlbum(AmnioticHomeAssistantMqttSensor):
    """

    Home Assistant Album sensor

    """
    META_KEY = 'Album'


class AmnioticHomeAssistantMqttSensorDate(AmnioticHomeAssistantMqttSensor):
    """

    Home Assistant Date sensor

    """
    META_KEY = 'Date'


class AmnioticHomeAssistantMqttSensorBy(AmnioticHomeAssistantMqttSensor):
    """

    Home Assistant By (Artist) sensor

    """
    META_KEY = 'Artist'


class AmnioticHomeAssistantMqttSensorDuration(AmnioticHomeAssistantMqttSensor):
    """

    Home Assistant Duration sensor

    """
    META_KEY = 'duration'
    IS_SOURCE_META = False

    def get_value(self, amniotic: Amniotic, key: Optional[str] = None):
        """

        Get the value in milliseconds from the status, change to per-second granularity and return as string.

        """
        milliseconds = super().get_value(amniotic)

        if milliseconds == self.NA_VALUE or milliseconds < 0:
            return super().NA_VALUE

        delta = timedelta(milliseconds=milliseconds)
        delta -= timedelta(microseconds=delta.microseconds)
        delta_str = str(delta)

        return delta_str


class AmnioticHomeAssistantMqttSensorElapsed(AmnioticHomeAssistantMqttSensorDuration):
    """

    Home Assistant Elapsed sensor

    """
    META_KEY = 'elapsed'


class AmnioticMqttEventLoop:
    """

    MQTT Event Loop

    """
    CONNECTION_MESSAGES = [
        "Connection successful",
        "Connection refused - incorrect protocol version",
        "Connection refused - invalid client identifier",
        "Connection refused - server unavailable",
        "Connection refused - bad username or password",
        "Connection refused - not authorised",
    ]
    LOOP_PERIOD = 1

    def on_message(self, client: mqtt.Client, amniotic: Amniotic, mqtt_message: mqtt.MQTTMessage):
        """

        Wrapper callback. Process payload and select and call the relevant entity object callback handler (`handle_incoming`) method.

        """

        func = self.callback_map[mqtt_message.topic]

        try:
            payload = json.loads(mqtt_message.payload.decode())
        except JSONDecodeError:
            payload = mqtt_message.payload.decode()

        logging.info(f'Incoming: {Message(func, mqtt_message.topic, payload)}')

        return func(client, self.queue, amniotic, payload)

    def on_connect_fail(self, client: mqtt.Client, amniotic: Amniotic):
        """

        Connection failed callback.

        """
        logging.error('Connection to MQTT lost.')

    def on_connect(self, client: mqtt.Client, amniotic: Amniotic, flags: dict, code: int):
        """

        Connection established/failed callback.

        """

        msg = f'Attempting to connect to MQTT "{client._host}:{client._port}": {self.CONNECTION_MESSAGES[code]}'
        if code:
            logging.error(msg)
        else:
            logging.info(msg)

        self.has_reconnected = True

    def __init__(self, host, port, entities: list[AmnioticHomeAssistantMqttEntity], amniotic: Amniotic, username: str = None, password: str = None,
                 tele_period: int = 300):
        """

        Setup and connect MQTT Client.

        """

        self.queue = []
        self.tele_period = tele_period
        self.has_reconnected = True
        self.topic_lwt = next(iter(entities)).device.topic_lwt
        self.entities = entities
        self.amniotic = amniotic
        self.client = mqtt.Client()
        self.callback_map = {
            entity.topic_command: entity.handle_incoming
            for entity in entities
        }
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_connect_fail = self.on_connect_fail
        self.client.user_data_set(amniotic)
        self.client.will_set(self.topic_lwt, payload='Offline', qos=1, retain=False, properties=None)

        if username is not None and password is not None:
            self.client.username_pw_set(username=username, password=password)

        self.client.connect(host=host, port=port)

    def handle_outgoing(self, force_announce=False):
        """

        Call entity outgoing methods to add to message queue.

        """

        for entity in self.entities:
            entity.handle_outgoing(self.client, self.queue, self.amniotic, force_announce=force_announce)

    def do_telemetry(self):
        """

        Send LWT message.

        """
        status = json.dumps(self.amniotic.status)
        logging.info(f'Telemetry: LWT')
        logging.debug(f'Status: {status}')
        # self.client.publish(TOPIC_STATUS, status)
        self.client.publish(self.topic_lwt, "Online", qos=1)
        self

    def loop_start(self):
        """

        Run Event Loop. Once connected, periodically aggregate entity messages into the queue, send queue messages, send LWT/telemetry.

        """

        self.client.loop_start()

        loop_count = 0

        while not self.client.is_connected():
            sleep(self.LOOP_PERIOD)

        while True:

            if not self.client.is_connected():
                sleep(self.LOOP_PERIOD)
                continue

            is_telem_loop = loop_count % self.tele_period == 0

            self.handle_outgoing(force_announce=self.has_reconnected)
            self.has_reconnected = False

            while self.queue:
                message = self.queue.pop(0)
                logging.info(f'Queue: {message}')
                message.send()

            if is_telem_loop:
                self.do_telemetry()

            sleep(self.LOOP_PERIOD)
            loop_count += 1


def start():
    """

    Load config, set up amniotic, MQTT devices and entities, and start MQTT event loop.

    """
    config = Config.from_file()
    logging.basicConfig(
        format='%(asctime)s %(levelname)-5s amniotic.%(module)-8s: %(message)s',
        level=config.logging,
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True
    )

    amniotic = Amniotic(path_base=config.path_audio, device_names=config.device_names)
    msg = f'Amniotic {__version__} has started.'
    logging.info(msg)
    msg = f'Amniotic {__version__} starting MQTT...'
    logging.info(msg)

    mqtt_device = AmnioticHomeAssistantMqttDevice(name=config.name, location=config.location)
    theme = AmnioticHomeAssistantMqttSelectTheme(mqtt_device, 'Theme', icon='surround-sound', )
    volume_master = AmnioticHomeAssistantMqttVolumeMaster(mqtt_device, 'Master Volume', icon='volume-high')
    volume_theme = AmnioticHomeAssistantMqttVolumeTheme(mqtt_device, 'Theme Volume', icon='volume-medium')
    device = AmnioticHomeAssistantMqttSelectDevice(mqtt_device, 'Theme Device', icon='expansion-card-variant')
    enabled = AmnioticHomeAssistantMqttEnabled(mqtt_device, 'Theme Enabled', 'play-circle')

    sensor = AmnioticHomeAssistantMqttSensorTitle(mqtt_device, 'Title', icon='rename-box')
    sensor_album = AmnioticHomeAssistantMqttSensorAlbum(mqtt_device, 'Album', icon='album')
    sensor_date = AmnioticHomeAssistantMqttSensorDate(mqtt_device, 'Date', icon='calendar-outline')
    sensor_by = AmnioticHomeAssistantMqttSensorBy(mqtt_device, 'By', icon='account')
    sensor_duration = AmnioticHomeAssistantMqttSensorDuration(mqtt_device, 'Duration', icon='timer')
    sensor_elapsed = AmnioticHomeAssistantMqttSensorElapsed(mqtt_device, 'Elapsed', icon='clock-time-twelve-outline')

    loop = AmnioticMqttEventLoop(
        amniotic=amniotic,
        entities=[theme, device, volume_master, volume_theme, enabled, sensor, sensor_album, sensor_date, sensor_by, sensor_duration, sensor_elapsed],
        host=config.mqtt_host,
        port=config.mqtt_port,
        username=config.mqtt_username,
        password=config.mqtt_password,
        tele_period=config.tele_period
    )

    loop.loop_start()


if __name__ == '__main__':
    start()
