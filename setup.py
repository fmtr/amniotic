from pathlib import Path
from setuptools import find_packages, setup

import requirements

name = 'amniotic'

path_base = Path(__file__).absolute().parent
path = path_base / name / 'version'
__version__ = path.read_text().strip()

packages = find_packages(where=path_base)
packages = [name] + [f'{name}.{nsp}' for nsp in packages]

setup(
    long_description=(path_base / 'readme.md').read_text(),
    long_description_content_type='text/markdown',
    name=name,
    version=__version__,
    url=f'https://fmtr.link/{name}',
    license='Copyright © 2022 Frontmatter. All rights reserved.',
    author='Frontmatter',
    description='A multi-output ambient sound mixer for Home Assistant',
    keywords='ambient sound audio white noise masking sleep',
    packages=packages,
    package_dir={'': '.'},
    package_data={
        name: [f'version'],
    },
    install_requires=requirements.INSTALL,
    extras_require=requirements.EXTRAS,
    entry_points={
        'console_scripts': [
            'amniotic = amniotic.mqtt.start:start',
        ],
    }
)

