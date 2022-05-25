import json
import re
from dataclasses import dataclass
from typing import Callable, Any

WHITESPACE = re.compile('[\s\-_]+')

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


def sanitize(*strings, sep: str = '-') -> str:
    """

    Replace spaces with URL- and ID-friendly characters, etc.

    """

    strings = [string for string in strings if string]
    string = ' '.join(strings)
    strings = [c.lower() for c in string if c.isalnum() or c in {' '}]
    string = ''.join(strings)
    string = WHITESPACE.sub(sep, string).strip()

    return string
