from datetime import timedelta
from typing import Optional, Union

from amniotic.mqtt import control


class Sensor(control.Entity):
    """

    Base Home Assistant Theme sensor entity, sends messages taken from current Theme status data.

    """
    HA_PLATFORM = 'sensor'
    NA_VALUE = '-'
    META_KEY = None
    IS_SOURCE_META = True
    UOM = None

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

    def set_value(self, value):
        pass

    def get_value(self, key=None) -> Union[str, int, float]:
        """

        Get the relevant value from the Theme status or metadata dictionaries

        """
        key = key or self.META_KEY
        status = self.amniotic.theme_current.status
        if self.IS_SOURCE_META:
            status = status.get('meta_data') or {}
        meta_value = status.get(key) or self.NA_VALUE
        return meta_value


class Title(Sensor):
    """

    Home Assistant Title sensor

    """

    NAME = META_KEY = 'Title'


class Album(Sensor):
    """

    Home Assistant Album sensor

    """
    NAME = META_KEY = 'Album'


class Date(Sensor):
    """

    Home Assistant Date sensor

    """
    NAME = META_KEY = 'Date'


class By(Sensor):
    """

    Home Assistant By (Artist) sensor

    """
    META_KEY = 'Artist'
    NAME = 'By'


class Duration(Sensor):
    """

    Home Assistant Duration sensor

    """
    META_KEY = 'duration'
    NAME = 'Duration'
    IS_SOURCE_META = False

    def get_value(self, key: Optional[str] = None):
        """

        Get the value in milliseconds from the status, change to per-second granularity and return as string.

        """
        milliseconds = super().get_value()

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
    NAME = 'Elapsed'
