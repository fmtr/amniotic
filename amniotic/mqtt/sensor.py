from datetime import timedelta
from typing import Optional, Union

from paho.mqtt import client as mqtt

from amniotic.audio import Amniotic
from amniotic.mqtt import control
from amniotic.mqtt.tools import Message


class Sensor(control.Entity):
    """

    Base Home Assistant Theme sensor entity, sends messages taken from current Theme status data.

    """
    HA_PLATFORM = 'sensor'
    NA_VALUE = '-'
    META_KEY = None
    IS_SOURCE_META = True
    UOM = None

    def __init__(self, device: control.Device, name: str, icon: Optional[str] = None):
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


class Title(Sensor):
    """

    Home Assistant Title sensor

    """
    META_KEY = 'Title'


class Album(Sensor):
    """

    Home Assistant Album sensor

    """
    META_KEY = 'Album'


class Date(Sensor):
    """

    Home Assistant Date sensor

    """
    META_KEY = 'Date'


class By(Sensor):
    """

    Home Assistant By (Artist) sensor

    """
    META_KEY = 'Artist'


class Duration(Sensor):
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


class Elapsed(Duration):
    """

    Home Assistant Elapsed sensor

    """
    META_KEY = 'elapsed'
