import logging
from copy import deepcopy
from dataclasses import dataclass, fields, field
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Dict, Optional

import yaml
from _socket import gethostname
from appdirs import AppDirs
from distutils.util import strtobool
from getmac import getmac

NAME = 'amniotic'
ORG = 'frontmatter'
APP_DIRS = AppDirs(NAME, ORG)
MAC_ADDRESS = getmac.get_mac_address().replace(':', '')
HOSTNAME = gethostname()
IS_ADDON = bool(strtobool(getenv(f'{NAME}_IS_ADDON'.upper(), 'false')))
PRESET_LAST_KEY = '.LAST'

DEVICE_NAMES_DEFAULT = {
    'alsa_output.platform-bcm2835_audio.stereo-fallback': 'Broadcom BCM2835 HDMI',
    'alsa_output.platform-bcm2835_audio.stereo-fallback.2': 'Broadcom BCM2835 Headphones/Line-Out',
}


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
    debug: bool = False
    tele_period: int = 300
    presets: dict = field(default_factory=dict)
    config_raw: dict = field(default_factory=dict)


    def __post_init__(self):
        path_audio = Path(self.path_audio).absolute()
        if not path_audio.exists():
            logging.warning(f'Audio path not found: "{path_audio}"')

        self.tele_period = round(self.tele_period)
        self.mqtt_port = int(self.mqtt_port)
        self.logging = self.logging or logging.INFO
        self.device_names = DEVICE_NAMES_DEFAULT | (self.device_names or {})

    @classmethod
    @lru_cache
    def get_path_config(cls) -> Path:
        """

        Get path to config file from environment variable, or default location

        """
        path_config = getenv('AMNIOTIC_CONFIG_PATH')

        if not path_config:
            path_config = Path(APP_DIRS.user_config_dir) / 'config.yml'
            path_config.parent.mkdir(parents=True, exist_ok=True)

        path_config = Path(path_config).absolute()

        return path_config

    @classmethod
    def from_file(cls):

        path_config = cls.get_path_config()

        if not path_config.exists():
            msg = f'Config file not found at "{path_config}". Default values will be used.'
            logging.warning(msg)
            config = {}
        else:
            msg = f'Config file found at "{path_config}"'
            logging.info(msg)
            config_str = Path(path_config).read_text()
            config = yaml.safe_load(config_str)

        config['config_raw'] = deepcopy(config)

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

    def write(self) -> int:
        """

        Write out current config to same path from where it was read

        """
        config_str = yaml.dump(self.config_raw)
        path = self.get_path_config()
        logging.info(f'Wrote out config file to: {path}')

        return path.write_text(config_str)

    def write_presets(self, presets: Dict, preset_last: Optional[Dict] = None) -> int:
        """

        Write out current config to same path from where it was read

        """

        presets = deepcopy(presets)  # Don't modify the original dictionary
        if preset_last:
            presets[PRESET_LAST_KEY] = preset_last

        self.config_raw['presets'] = presets

        return self.write()
