import json
import logging
import re
from dataclasses import dataclass
from time import sleep
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
    is_announce: bool = False

    def __post_init__(self):
        """

        If data requires JSON serialization, apply it.

        """
        if self.serialize:
            self.data = json.dumps(self.data)

    @property
    def is_publish(self):
        """

        Is this a publish message?

        """
        return self.method.__name__ == 'publish' and not self.is_announce

    @property
    def is_subscribe(self):
        """

        Is this a subscribe message?

        """
        return self.method.__name__ == 'subscribe'

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

    @classmethod
    def send_many(self, messages: list['Message'], delay: float = 0.5):
        """

        Send message types (announce/sub/pub) in distinct batches.

        """
        announces = [message for message in messages if message.is_announce]
        subscriptions = [message for message in messages if message.is_subscribe]
        publishes = [message for message in messages if message.is_publish]
        batches = [announces, subscriptions, publishes]

        do_delays = [True, True, False]

        for batch, do_delay in zip(batches, do_delays):

            for message in batch:
                logging.info(f'Queue: {message}')
                message.send()

            if batch and do_delay:
                sleep(delay)


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


