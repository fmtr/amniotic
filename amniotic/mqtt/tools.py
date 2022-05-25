import json
from dataclasses import dataclass
from typing import Callable, Any


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
