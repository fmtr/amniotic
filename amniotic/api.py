from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.requests import Request

from amniotic.obs import logger
from amniotic.paths import paths
from amniotic.theme import ThemeDefinition, ThemeStream
from corio import api, mqtt

class ApiAmniotic(api.Base):
    TITLE = f'Amniotic {paths.metadata.version} Streaming API'
    URL_DOCS = '/'
    PORT =  8000+paths.metadata.port+(1000 if paths.repo else 0)

    def __init__(self, client: mqtt.Client):
        super().__init__()

        self.client = client

    @property
    def ENDPOINTS(self):
        return [Stream]


class Stream(api.endpoint.API):
    """Stream a theme's audio."""

    PATH = '/stream/{id}'

    async def run(self, id: str, request: Request):
        logger.info(f'Got streaming audio request {id=} {request.client=}')
        theme_def: ThemeDefinition = self.api.client.device.themes.id[id]
        stream = ThemeStream(theme_def=theme_def, request=request)

        if not stream.is_enabled:
            logger.warning(f'Theme "{theme_def.name}" is streaming, but it has no recordings enabled. The stream will be silent. Enable some recordings to hear output.')

        response = StreamingResponse(
            stream,
            media_type="audio/mpeg",
            background=BackgroundTask(stream.close),
        )
        return response



if __name__ == '__main__':
    ApiAmniotic.launch()
