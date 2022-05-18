import ast

from setuptools import find_packages, setup

packages = find_packages()
__version__ = open(f'{next(iter(packages))}/version').read()

setup(
    name='amniotic',
    version=__version__,
    url='https://github.com/ejohb/amniotic',
    license='Copyright © 2022 Frontmatter. All rights reserved.',
    author='Frontmatter',
    description='Amniotic',
    packages=packages,
    package_data={},
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
