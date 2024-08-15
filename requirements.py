INSTALL = [
    'paho-mqtt',
    'python-vlc',
    'getmac',
    'pyyaml',
    'appdirs',
    'johnnydep',
    'pytube',
    'cachetools',

    'fastapi',
    'av',
    'uvicorn',
    'ffmpeg-python',
    'numpy',
    'pydub'
]

EXTRAS = {}

if __name__ == '__main__':
    import sys

    reqs = []
    reqs += INSTALL
    if len(sys.argv) > 1:
        for extra in sys.argv[1].split(','):
            reqs += EXTRAS[extra]
    reqs = '\n'.join(reqs)
    print(reqs)
