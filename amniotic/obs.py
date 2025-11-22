from fmtr.tools import logging, debug, Constants

from amniotic.paths import paths
from amniotic.version import __version__

debug.trace()

logger = logging.get_logger(
    name=paths.name_ns,
    stream=Constants.DEVELOPMENT,
    version=__version__,
)
