from pathlib import Path

path = Path(__file__).absolute().parent / 'version'
__version__ = path.read_text().strip()
