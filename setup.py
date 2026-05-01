from corio import Setup

setup = Setup(
    dependencies=dict(
        install=[
            'corio[version.dev,logging,sets,yaml,debug,caching,api,mqtt,path.app,tabular,av,ha.api,http,youtube]',
            'haco',
            'psutil'
        ],
        test=[
            'pytest>=8.0',
            'pytest-asyncio>=0.24',
        ],
    ),
    description='A multi-output ambient sound mixer for Home Assistant',
    keywords='ambient sound audio white noise masking sleep',
)

