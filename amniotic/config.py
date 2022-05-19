import logging
from dataclasses import dataclass
from os import getenv
from pathlib import Path

import yaml
from appdirs import AppDirs

from .version import __version__


@dataclass
class Config:
    """

    """
    name: str = None
    mqtt_host: str = 'homeassistant.local'
    mqtt_port: int = 1883
    mqtt_username: str = None
    mqtt_password: str = None
    location: str = None
    path_audio: str = 'audio'
    device_names: dict = None
    logging: str = None

    def __post_init__(self):
        path_audio = Path(self.path_audio)
        if not path_audio.exists():
            logging.warning(f'Audio path not found. {path_audio}')

        self.logging = self.logging or 'INFO'

    @classmethod
    def from_file(cls):

        PATH_CONFIG_BASE = getenv('SC_CONFIG_BASE')
        dirs = AppDirs("amniotic", "frontmatter", version=__version__)

        if not PATH_CONFIG_BASE:
            PATH_CONFIG_BASE = dirs.site_config_dir

        path_config = Path(PATH_CONFIG_BASE) / 'config.yml'

        if not path_config.exists():
            logging.warning(f'Config file not found. Default values will be used. {path_config}')
            config = {}
        else:
            config = yaml.safe_load(Path(path_config).read_text())

        config = cls(**config)
        return config
