from amniotic.paths import paths
from fmtr.tools import infra


class Project(infra.Project):
    """"""

    def __init__(self, entrypoint=None, hostname='ws.lan', channel='dev', extras=None):
        super().__init__(

            # project
            base='python',
            name=paths.name_ns,
            port=7,

            is_dockerhub=True,
            is_pypi=True,

            scripts=[],
            entrypoint=entrypoint,
            hostname=hostname,
            channel=channel,
            extras=extras
        )
