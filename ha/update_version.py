import sys
from pathlib import Path

import yaml

ENCODING = 'UTF-8'
PATH_ADDON = Path(__file__).absolute().parent
PATH = PATH_ADDON / 'config.yaml'

if __name__ == '__main__':
    version = sys.argv[1]

    config = yaml.safe_load(PATH.read_text(encoding=ENCODING))
    config['version'] = version
    PATH.write_text(yaml.dump(config), encoding=ENCODING)
