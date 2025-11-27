import logging

from fastapi.responses import StreamingResponse

from amniotic.v2.theme import ThemeDefinition
from fmtr.tools import api, mqtt

for name in ["uvicorn.access", "uvicorn.error", "uvicorn"]:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False


class ApiAmniotic(api.Base):
    TITLE = 'Amniotic Test API'
    URL_DOCS = '/'

    def __init__(self, client: mqtt.Client):
        super().__init__()

        self.client = client

    def get_endpoints(self):
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/stream/{id}', method=self.stream),

        ]

        return endpoints

    async def stream(self, id: str):
        theme_def: ThemeDefinition = self.client.device.theme_lookup_id[id]
        stream = theme_def.get_stream()

        response = StreamingResponse(stream, media_type="audio/mpeg")

        return response



if __name__ == '__main__':
    ApiAmniotic.launch()
