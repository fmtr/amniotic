import logging as logging_native

from amniotic.paths import paths
from corio import logging, debug, Constants
from corio.environment_tools import get_bool

debug.trace()

logger = logging.get_logger(
    name=paths.name_ns,
    stream=Constants.DEVELOPMENT,
    version=paths.metadata.version,
    level=logging_native.DEBUG if get_bool(Constants.FMTR_DEV_KEY, default=False) else logging_native.INFO  # todo: fix runtime environment for addons
)
