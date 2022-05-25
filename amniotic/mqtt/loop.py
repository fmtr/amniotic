import json
import logging
from json import JSONDecodeError
from time import sleep

from paho.mqtt import client as mqtt

from amniotic.audio import Amniotic
from amniotic.config import Config
from amniotic.mqtt import control, sensor
from amniotic.mqtt.tools import Message
from amniotic.version import __version__


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

    def __init__(self, host, port, entities: list[control.Entity], amniotic: Amniotic, username: str = None, password: str = None,
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

    mqtt_device = control.Device(name=config.name, location=config.location)
    theme = control.SelectTheme(mqtt_device, 'Theme', icon='surround-sound', )
    volume_master = control.VolumeMaster(mqtt_device, 'Master Volume', icon='volume-high')
    volume_theme = control.VolumeTheme(mqtt_device, 'Theme Volume', icon='volume-medium')
    device = control.SelectDevice(mqtt_device, 'Theme Device', icon='expansion-card-variant')
    enabled = control.ToggleTheme(mqtt_device, 'Theme Enabled', 'play-circle')

    sensor_title = sensor.Title(mqtt_device, 'Title', icon='rename-box')
    sensor_album = sensor.Album(mqtt_device, 'Album', icon='album')
    sensor_date = sensor.Date(mqtt_device, 'Date', icon='calendar-outline')
    sensor_by = sensor.By(mqtt_device, 'By', icon='account')
    sensor_duration = sensor.Duration(mqtt_device, 'Duration', icon='timer')
    sensor_elapsed = sensor.Elapsed(mqtt_device, 'Elapsed', icon='clock-time-twelve-outline')

    loop = AmnioticMqttEventLoop(
        amniotic=amniotic,
        entities=[theme, device, volume_master, volume_theme, enabled, sensor_title, sensor_album, sensor_date, sensor_by, sensor_duration, sensor_elapsed],
        host=config.mqtt_host,
        port=config.mqtt_port,
        username=config.mqtt_username,
        password=config.mqtt_password,
        tele_period=config.tele_period
    )

    loop.loop_start()


if __name__ == '__main__':
    start()
