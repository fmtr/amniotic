from pathlib import Path

from setuptools import find_packages, setup

packages = find_packages()
name = next(iter(packages))
path = Path(__file__).absolute().parent / name / 'version'
__version__ = path.read_text()

setup(
    name=name,
    version=__version__,
    url=f'https://github.com/fmtr/{name}',
    license='Copyright © 2022 Frontmatter. All rights reserved.',
    author='Frontmatter',
    description='A multi-output, multi-theme ambient sound mixer for Home Assistant',
    packages=packages,
    package_data={
        name: [f'version'],
    },
    install_requires=[
        'paho-mqtt',
        'python-vlc',
        'getmac',
        'pyyaml',
        'appdirs'
    ],
    extras_require={},
    entry_points={
        'console_scripts': [
            'amniotic = amniotic.mqtt:start',
        ],
    }
)
