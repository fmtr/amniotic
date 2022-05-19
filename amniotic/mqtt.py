import json
import logging
from _socket import gethostname
from dataclasses import dataclass
from json import JSONDecodeError
from time import sleep
from typing import Any, Callable

import paho.mqtt.client as mqtt
from getmac import getmac

from .audio import Amniotic
from .config import Config
from .version import __version__

# from amniotic.logger import logging

MAC_ADDRESS = getmac.get_mac_address().replace(':', '')
HOSTNAME = gethostname()


@dataclass
class Message:
    method: Callable
    topic: str
    data: Any = None
    serialize: bool = False

    def __post_init__(self):
        if self.serialize:
            self.data = json.dumps(self.data)

    def __str__(self):
        return f'{self.method.__name__}:{self.topic}>{self.data}'

    def send(self):
        args = [] if self.data is None else [self.data]
        self.method(self.topic, *args)


def sanitize(string, sep='-'):
    return string.lower().strip().replace(' ', sep)


class AmnioticHomeAssistantMqttDevice:
    NAME_DEFAULT = 'Amniotic'
    MODEL_DEFAULT = 'Amniotic'
    MANUFACTURER = 'Frontmatter'
    URL = None

    def __init__(self, name=None, location=None):
        ...

        self.sw_version = __version__
        self._name = name or self.NAME_DEFAULT
        self.location = location

    @property
    def uid(self):
        return sanitize(f'{self.location or ""} {self.name} {MAC_ADDRESS}')

    @property
    def name(self):
        return f'{self.location or ""} {self._name}'.strip()

    @property
    def topic_lwt(self):
        subpath = sanitize(f'{self.location or ""} {self._name}'.strip(), sep='/')
        return f'tele/{subpath}/LWT'

    @property
    def data(self):
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
    PAYLOAD_ONLINE = "Online"
    PAYLOAD_OFFLINE = "Offline"
    DEVICE_CLASS = None
    name = None
    device = None
    _icon = None

    @property
    def data(self):
        data = {
            "name": self.name,
            "unique_id": self.uid,
            "device": self.device.data,
            "device_class": self.DEVICE_CLASS,
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
        path = f'homeassistant/{self.DEVICE_CLASS}/{subpath}/config'

        return path

    @property
    def icon(self):
        icon = f"mdi:{self._icon}" if self._icon else None
        return icon

    def handle_incoming(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, payload: Any):
        raise NotImplementedError()

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        if force_announce:
            queue += [
                Message(client.publish, self.topic_announce, self.data, serialize=True),
                Message(client.subscribe, self.topic_command),
            ]


class AmnioticHomeAssistantMqttVolume(AmnioticHomeAssistantMqttEntity):
    DEVICE_CLASS = 'number'

    def __init__(self, device: AmnioticHomeAssistantMqttDevice, name: str, icon=None, min=0, max=100, ):
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
    DEVICE_CLASS = 'number'

    def __init__(self, device: AmnioticHomeAssistantMqttDevice, name: str, icon=None, min=0, max=100, ):
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

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):

        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)
        value = amniotic.volume
        if value != self.value or force_announce:
            message = Message(client.publish, self.topic_state, value)
            queue.append(message)
            self.value = value

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        if payload is not None:
            amniotic.set_volume(payload)
        message = Message(client.publish, self.topic_state, amniotic.volume)
        queue.append(message)


class AmnioticHomeAssistantMqttVolumeChannel(AmnioticHomeAssistantMqttVolume):

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):

        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)
        value = amniotic.channel_current.volume
        if value != self.value or force_announce:
            message = Message(client.publish, self.topic_state, value)
            queue.append(message)
            self.value = value

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        if payload is not None:
            amniotic.set_volume_channel(payload)
        message = Message(client.publish, self.topic_state, amniotic.channel_current.volume)
        queue.append(message)


class AmnioticHomeAssistantMqttSelect(AmnioticHomeAssistantMqttEntity):
    DEVICE_CLASS = 'select'

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
        data = super().data | {
            'options': self.options
        }
        return data

    def get_select_state(self, amniotic: Amniotic):
        raise NotImplementedError()

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):

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


class AmnioticHomeAssistantMqttSelectChannel(AmnioticHomeAssistantMqttSelect):
    ...

    def get_select_state(self, amniotic: Amniotic):
        return list(amniotic.channels.keys()), amniotic.channel_current.name

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        if payload is not None:
            amniotic.set_channel(payload)
        message = Message(client.publish, self.topic_state, amniotic.channel_current.name)
        queue.append(message)


class AmnioticHomeAssistantMqttSelectDevice(AmnioticHomeAssistantMqttSelect):

    def get_select_state(self, amniotic: Amniotic):
        return list(amniotic.devices.values()), amniotic.channel_current.device_name

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        if payload is not None:
            amniotic.channel_current.set_device(payload)
        message = Message(client.publish, self.topic_state, amniotic.channel_current.device_name)
        queue.append(message)


class AmnioticHomeAssistantMqttSwitch(AmnioticHomeAssistantMqttEntity):
    DEVICE_CLASS = 'switch'
    ...

    VALUE_MAP = [(OFF := 'OFF'), (ON := 'ON')]

    def __init__(self, device: AmnioticHomeAssistantMqttDevice, name: str, icon=None):
        self.device = device
        self.name = name
        self._icon = icon
        self.value = None

    def handle_incoming(self, client: mqtt.Client, queue, amniotic: Amniotic, payload: Any):
        if payload is not None:
            amniotic.channel_current.enabled = payload == self.ON
        message = Message(client.publish, self.topic_state, self.VALUE_MAP[amniotic.channel_current.enabled])
        queue.append(message)

    def handle_outgoing(self, client: mqtt.Client, queue: list[Message], amniotic: Amniotic, force_announce=False):
        super().handle_outgoing(client, queue, amniotic, force_announce=force_announce)

        value = amniotic.channel_current.enabled
        if value != self.value or force_announce:
            message = Message(client.publish, self.topic_state, self.VALUE_MAP[amniotic.channel_current.enabled])
            queue.append(message)
            self.value = value

    @property
    def data(self):
        data = super().data | {
            'device_class': 'outlet',
        }
        return data


class AmnioticEventLoop:
    CONNECTION_MESSAGES = [
        "Connection successful",
        "Connection refused - incorrect protocol version",
        "Connection refused - invalid client identifier",
        "Connection refused - server unavailable",
        "Connection refused - bad username or password",
        "Connection refused - not authorised",
    ]

    def on_message(self, client: mqtt.Client, amniotic: Amniotic, msg):

        func = self.callback_map[msg.topic]

        try:
            payload = json.loads(msg.payload.decode())
        except JSONDecodeError:
            payload = msg.payload.decode()

        logging.info(f'Incoming: {Message(func, msg.topic, payload)}')

        return func(client, self.queue, amniotic, payload)

    def on_connect_fail(self, client, amniotic):
        logging.error('Connection to MQTT lost.')

    def on_connect(self, client: mqtt.Client, amniotic, flags, code):

        msg = f'Attempting to connect to MQTT "{client._host}:{client._port}": {self.CONNECTION_MESSAGES[code]}'
        if code:
            logging.error(msg)
        else:
            logging.info(msg)

        self.has_reconnected = True

    def __init__(self, host, port, entities: list[AmnioticHomeAssistantMqttEntity], amniotic: Amniotic, usename=None, password=None):

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
        self.client.will_set(self.topic_lwt, payload='Offline', qos=0, retain=False, properties=None)

        if usename is not None and password is not None:
            self.client.username_pw_set(username=usename, password=password)

        self.client.connect(host=host, port=port)

        self.queue = []

        # self.loop_start()

    def handle_outgoing(self, force_announce=False):

        for entity in self.entities:
            entity.handle_outgoing(self.client, self.queue, self.amniotic, force_announce=force_announce)

    def do_telemetry(self):
        status = json.dumps(self.amniotic.status)
        logging.info(f'Telemetry: LWT')
        logging.debug(f'Status: {status}')
        # self.client.publish(TOPIC_STATUS, status)
        self.client.publish(self.topic_lwt, "Online")

    def do_entity_messages(self):
        pass

    def loop_start(self):

        self.client.loop_start()

        tele_period = 60
        loop_count = 0
        loop_period = 1

        while not self.client.is_connected():
            sleep(loop_period)

        while True:

            if not self.client.is_connected():
                continue

            is_telem_loop = loop_count % tele_period == 0

            self.handle_outgoing(force_announce=self.has_reconnected)
            self.has_reconnected = False

            while self.queue:
                message = self.queue.pop(0)
                logging.info(f'Queue: {message}')
                message.send()

            if is_telem_loop:
                self.do_telemetry()

            sleep(loop_period)
            loop_count += 1


def start():
    config = Config.from_file()
    logging.basicConfig(
        format='%(asctime)s %(levelname)-5s amniotic.%(module)-8s: %(message)s',
        level=config.logging,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    mqtt_device = AmnioticHomeAssistantMqttDevice(name=config.name, location=config.location)
    channel = AmnioticHomeAssistantMqttSelectChannel(mqtt_device, 'Channel', icon='surround-sound', )
    volume_master = AmnioticHomeAssistantMqttVolumeMaster(mqtt_device, 'Master Volume', icon='volume-high')
    volume_current = AmnioticHomeAssistantMqttVolumeChannel(mqtt_device, 'Current Volume', icon='volume-medium')
    device = AmnioticHomeAssistantMqttSelectDevice(mqtt_device, 'Channel Device', icon='expansion-card-variant')
    enabled = AmnioticHomeAssistantMqttSwitch(mqtt_device, 'Channel Enabled', 'play-circle')
    amniotic = Amniotic(path_base=config.path_audio, device_names=config.device_names)

    loop = AmnioticEventLoop(
        amniotic=amniotic,
        entities=[channel, device, volume_master, volume_current, enabled],
        host=config.mqtt_host,
        port=config.mqtt_port,
        usename=config.mqtt_username,
        password=config.mqtt_password
    )

    loop.loop_start()


if __name__ == '__main__':
    start()
