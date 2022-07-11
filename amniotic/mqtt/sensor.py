from datetime import timedelta
from typing import Optional, Union, Any

from amniotic.mqtt import control
from amniotic.version import __version__


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
        if self.UOM:
            data['unit_of_measurement'] = self.UOM
        return data

    def set_value(self, value: Any):
        """

        Dummy method.

        """
        pass

    def get_value(self, key=None) -> Union[str, int, float]:
        """

        Get the relevant value from the Theme status or metadata dictionaries

        """
        key = key or self.META_KEY
        status = self.amniotic.theme_current.status
        if self.IS_SOURCE_META:
            status = status.get('meta_data') or {}
        meta_value = status.get(key)
        if meta_value is None:
            meta_value = self.NA_VALUE
        return meta_value


class Title(Sensor):
    """

    Home Assistant Title sensor

    """

    NAME = META_KEY = 'Title'
    ICON_SUFFIX = 'text-recognition'


class Album(Sensor):
    """

    Home Assistant Album sensor

    """
    NAME = META_KEY = 'Album'
    ICON_SUFFIX = 'album'


class Date(Sensor):
    """

    Home Assistant Date sensor

    """
    NAME = META_KEY = 'Date'
    ICON_SUFFIX = 'calendar-outline'


class By(Sensor):
    """

    Home Assistant By (Artist) sensor

    """
    META_KEY = 'Artist'
    NAME = 'By'
    ICON_SUFFIX = 'account'


class Duration(Sensor):
    """

    Home Assistant Duration sensor

    """
    META_KEY = 'duration'
    NAME = 'Duration'
    IS_SOURCE_META = False
    ICON_SUFFIX = 'timer'

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
    ICON_SUFFIX = 'clock-time-twelve-outline'


class StaticMessageSensor(Sensor):
    """

    Base Home Assistant static message sensor. Just reports a static message. The message will be set by other controls.

    """

    message = Sensor.NA_VALUE

    def get_value(self, key=None) -> Union[str, int, float]:
        """

        Return current message

        """
        return self.message


class UpdateStatus(StaticMessageSensor):
    """

    Home Assistant update status sensor. Messages set by Check Update button etc.

    """
    NAME = 'Update Status'
    ICON_SUFFIX = 'semantic-web'
    message = 'Never checked'


class DownloaderStatus(StaticMessageSensor):
    """

    Home Assistant downloader status sensor. Messages set by downloader input etc.

    """
    NAME = 'Downloader Status'
    ICON_SUFFIX = 'cloud-sync-outline'
    message = 'Idle'


class TrackCount(Sensor):
    """

    Home Assistant Track Count sensor

    """
    META_KEY = 'track_count'
    NAME = 'Track Count'
    IS_SOURCE_META = False
    ICON_SUFFIX = 'pound-box'

    def get_value(self, key=None) -> Union[str, int, float]:
        """

        Update theme from disk before reporting track count.

        """
        self.amniotic.theme_current.update_paths()
        return super().get_value(key)


class Version(StaticMessageSensor):
    """

    Home Assistant version number sensor

    """

    NAME = 'Current Version'
    ICON_SUFFIX = 'counter'
    message = __version__
