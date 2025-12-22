from fastapi.responses import StreamingResponse
from starlette.requests import Request

from amniotic.obs import logger
from amniotic.theme import ThemeDefinition, ThemeStream
from amniotic.version import __version__
from fmtr.tools import api, mqtt


class ApiAmniotic(api.Base):
    TITLE = f'Amniotic {__version__} Streaming API'
    URL_DOCS = '/'

    def __init__(self, client: mqtt.Client):
        super().__init__()

        self.client = client

    def get_endpoints(self):
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/stream/{id}', method=self.stream),

        ]

        return endpoints

    async def stream(self, id: str, request: Request):
        logger.info(f'Got streaming audio request {id=} {request.client=}')
        theme_def: ThemeDefinition = self.client.device.themes.id[id]
        stream = ThemeStream(theme_def=theme_def, request=request)


        if not stream.is_enabled:
            logger.warning(f'Theme "{theme_def.name}" is streaming, but it has no recordings enabled. The stream will be silent. Enable some recordings to hear output.')

        response = StreamingResponse(stream, media_type="audio/mpeg")
        return response



if __name__ == '__main__':
    ApiAmniotic.launch()
