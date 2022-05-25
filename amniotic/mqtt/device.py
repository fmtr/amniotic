from typing import Optional

from amniotic.config import MAC_ADDRESS
from amniotic.mqtt.tools import sanitize
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
