from fmtr.tools import Setup

setup = Setup(
    org=None,
    dependencies=dict(
        install=[
            'fmtr.tools[version.dev,logging,sets,yaml,debug,caching,api,mqtt,path.app,tabular,av]',
            'haco==1.0.0alpha004',
            'homeassistant_api'
        ]
    ),
    description='A multi-output ambient sound mixer for Home Assistant',
    keywords='ambient sound audio white noise masking sleep',
    # url=f'https://fmtr.link/{name}',
)


