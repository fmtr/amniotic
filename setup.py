from pathlib import Path

from setuptools import find_packages, setup

packages = find_packages()
name = next(iter(packages))
path_base = Path(__file__).absolute().parent
path = path_base / name / 'version'
__version__ = path.read_text().strip()

setup(
    long_description=(path_base / 'readme.md').read_text(),
    long_description_content_type='text/markdown',
    name=name,
    version=__version__,
    url=f'https://link.frontmatter.ai/{name}',
    license='Copyright © 2022 Frontmatter. All rights reserved.',
    author='Frontmatter',
    description='A multi-output ambient sound mixer for Home Assistant',
    keywords='ambient sound audio white noise masking sleep',
    packages=packages,
    package_data={
        name: [f'version'],
    },
    install_requires=[
        'paho-mqtt',
        'python-vlc',
        'getmac',
        'pyyaml',
        'appdirs',
        'johnnydep',
        'pytube',
        'cachetools'
    ],
    extras_require={},
    entry_points={
        'console_scripts': [
            'amniotic = amniotic.mqtt.loop:start',
        ],
    }
)
