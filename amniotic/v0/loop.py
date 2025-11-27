import json
import logging
from copy import deepcopy
from functools import cached_property
from json import JSONDecodeError
from time import sleep
from typing import Type

from amniotic.audio import Amniotic
from amniotic.config import Config, IS_ADDON, PRESET_LAST_KEY
from paho.mqtt import client as mqtt

from amniotic.v0.device import Device
from amniotic.v0.tools import Message
from amniotic.version import __version__


class Loop:
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
    DELAY = 0.5
    DELAY_FIRST = 3

    def __init__(self, config: Config, device: Device, amniotic: Amniotic):
        """

        Setup and connect MQTT Client.

        """

        self.config = config
        self.device = device

        self.exit_reason = False

        self.entities = {
            entity_class: entity_class(self)
            for entity_class in self.entity_classes
        }
        self.callback_map = {
            entity.topic_command: entity.handle_incoming
            for entity in self.entities.values()
        }

        self.queue = []
        self.force_announce_period = self.config.tele_period * 10
        self.has_reconnected = True
        self.is_telem_loop = False
        self.topic_lwt = self.device.topic_lwt

        self.amniotic = amniotic
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_connect_fail = self.on_connect_fail
        self.client.user_data_set(amniotic)
        self.client.will_set(self.topic_lwt, payload='Offline', qos=1, retain=False, properties=None)

        if config.mqtt_username is not None and config.mqtt_password is not None:
            self.client.username_pw_set(username=config.mqtt_username, password=config.mqtt_password)

        msg = f'Attempting to connect to MQTT "{config.mqtt_host}:{config.mqtt_port}"...'
        logging.info(msg)

        try:
            self.client.connect(host=config.mqtt_host, port=config.mqtt_port)
        except Exception as exception:
            msg = f'Error connecting. This usually means your MQTT host is not available.'
            raise ConnectionError(msg) from exception


    def on_message(self, client: mqtt.Client, amniotic: Amniotic, mqtt_message: mqtt.MQTTMessage):
        """

        Wrapper callback. Process payload and select and call the relevant entity object callback handler (`handle_incoming`) method.

        """

        func = self.callback_map[mqtt_message.topic]

        try:
            value = json.loads(mqtt_message.payload.decode())
        except JSONDecodeError:
            value = mqtt_message.payload.decode()

        logging.info(f'Incoming: {Message(func, mqtt_message.topic, value)}')

        return func(value)

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

    @cached_property
    def entity_classes(self) -> list[Type]:
        """

        Import all entity/sensor classes, excluding Update-related ones if we're running as an HA addon

        """
        from amniotic.v0 import control, sensor

        controls = [
            control.VolumeMaster,
            control.VolumeAdjustThreshold,
            control.ButtonVolumeDownMaster,
            control.ButtonVolumeUpMaster,
            control.ButtonDisableAllThemes,

            control.ButtonRestart,

            control.SelectTheme,
            control.VolumeTheme,
            control.ToggleTheme,
            control.ToggleMergePresets,
            control.DeviceTheme,
            control.ButtonVolumeDownTheme,
            control.ButtonVolumeUpTheme,

            control.PresetData,
            control.Preset,
            control.SavePreset,
            control.DeletePreset,

            control.Downloader,
            control.NewTheme,

        ]

        if not IS_ADDON:
            controls += [
                control.ButtonUpdateCheck,
                control.ButtonUpdate,
            ]

        sensors = [
            sensor.Overview,
            sensor.Title,
            sensor.Album,
            sensor.TrackCount,
            sensor.Date,
            sensor.By,
            sensor.Duration,
            # sensor.Elapsed,
            sensor.DownloadStatus,
        ]

        if not IS_ADDON:
            sensors += [
                sensor.UpdateStatus,
                sensor.Version
            ]

        if self.config.debug:
            sensors += [
                sensor.CPU,
                sensor.Memory,
            ]

        return controls + sensors

    def handle_outgoing(self, force_announce=False):
        """

        Call entity outgoing methods to add to message queue.

        """

        for entity in self.entities.values():
            entity.handle_outgoing(force_announce=force_announce)

    def do_telemetry(self):
        """

        Send LWT message.

        """
        status = json.dumps(self.amniotic.status)
        logging.info(f'Telemetry: LWT')
        logging.info(f'Status: {status}')
        # self.client.publish(TOPIC_STATUS, status)
        self.client.publish(self.topic_lwt, "Online", qos=1)

    def loop_start(self):
        """

        Run Event Loop. Once connected, periodically aggregate entity messages into the queue, send queue messages, send LWT/telemetry.

        """

        self.client.loop_start()

        loop_count = 0

        while not self.client.is_connected():
            sleep(self.LOOP_PERIOD)

        while not self.exit_reason:

            if not loop_count:
                delay = self.DELAY_FIRST
            else:
                delay = self.DELAY

            if not self.client.is_connected():
                sleep(self.LOOP_PERIOD)
                continue

            self.is_telem_loop = loop_count % self.config.tele_period == 0
            is_force_announce_loop = loop_count % self.force_announce_period == 0

            self.handle_outgoing(force_announce=self.has_reconnected or is_force_announce_loop)
            self.has_reconnected = False

            Message.send_many(self.queue, delay=delay)
            self.queue.clear()

            if self.is_telem_loop:
                self.do_telemetry()

            sleep(self.LOOP_PERIOD)
            loop_count += 1

        self.close()

    def close(self):
        """

        Close Amniotic gracefully, save current config, etc.

        """
        msg = f'Event loop exiting gracefully for the following reason: {self.exit_reason}'
        logging.info(msg)

        msg = f'Adding current preset to config'
        logging.info(msg)

        presets = deepcopy(self.amniotic.presets)
        presets[PRESET_LAST_KEY] = self.amniotic.get_preset_data()
        self.config.config_raw['presets'] = presets
        self.config.write()

        msg = f'Amniotic {__version__} closing...'
        logging.info(msg)
        self.amniotic.close()


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

    preset_last = config.presets.pop(PRESET_LAST_KEY, None)
    amniotic = Amniotic(path=config.path_audio, device_names=config.device_names, presets=config.presets)
    if preset_last:
        amniotic.apply_preset_data(preset_last)

    msg = f'Amniotic {__version__} (libvlc {amniotic.VLC_VERSION}) has started.'
    logging.info(msg)
    msg = f'Amniotic {__version__} starting MQTT...'
    logging.info(msg)

    loop = Loop(
        config,
        device=Device(location=config.location),
        amniotic=amniotic,
    )

    loop.loop_start()