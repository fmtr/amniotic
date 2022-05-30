import json
import logging
from _socket import gethostname
from dataclasses import dataclass, fields
from distutils.util import strtobool
from os import getenv
from pathlib import Path

import yaml
from appdirs import AppDirs
from getmac import getmac

NAME = 'amniotic'
ORG = 'frontmatter'
APP_DIRS = AppDirs(NAME, ORG)
MAC_ADDRESS = getmac.get_mac_address().replace(':', '')
HOSTNAME = gethostname()
IS_ADDON = bool(strtobool(getenv(f'{NAME}_IS_ADDON'.upper(), 'false')))


@dataclass
class Config:
    """

    """
    mqtt_host: str = 'homeassistant.local'
    mqtt_port: int = 1883
    mqtt_username: str = None
    mqtt_password: str = None
    location: str = None
    path_audio: str = APP_DIRS.user_data_dir
    device_names: dict = None
    logging: str = None
    tele_period: int = 300

    def __post_init__(self):
        path_audio = Path(self.path_audio).absolute()
        if not path_audio.exists():
            logging.warning(f'Audio path not found: "{path_audio}"')

        self.tele_period = round(self.tele_period)
        self.mqtt_port = int(self.mqtt_port)
        self.logging = self.logging or logging.INFO

    @classmethod
    def from_file(cls):

        path_config = getenv('AMNIOTIC_CONFIG_PATH')

        if not path_config:
            path_config = Path(APP_DIRS.user_config_dir) / 'config.yml'
            path_config.parent.mkdir(parents=True, exist_ok=True)

        path_config = Path(path_config).absolute()

        if not path_config.exists():
            msg = f'Config file not found at "{path_config}". Default values will be used.'
            logging.warning(msg)
            config = {}
        else:
            msg = f'Config file found at "{path_config}"'
            logging.info(msg)

            config_str = Path(path_config).read_text()

            if path_config.suffix in {'.yml', '.yaml'}:
                config = yaml.safe_load(config_str)
            elif path_config.suffix in {'.json'}:
                config = json.loads(config_str)
            else:
                msg = f'Unknown config format "{path_config.suffix}"'
                raise ValueError(msg)

            logging.warning(msg)

        field_names = {field.name for field in fields(Config)}
        for key in field_names:
            key_env = f'{NAME}_{key}'.upper()
            if (val_env := getenv(key_env)):
                config[key] = val_env

        for key in set(config.keys()) - field_names:
            msg = f'Unknown config field "{key}". Will be ignored.'
            logging.warning(msg)
            config.pop(key)

        config = cls(**config)
        return config
