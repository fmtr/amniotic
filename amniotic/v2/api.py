import logging

from fastapi.responses import StreamingResponse

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
            api.Endpoint(method_http=self.app.get, path='/stream', method=self.stream),

        ]

        return endpoints



    async def stream(self):
        theme_def = self.client.device.theme_current

        stream = theme_def.get_stream()

        response = StreamingResponse(stream, media_type="audio/mpeg")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Connection"] = "close"  # Close the connection when done

        return response



if __name__ == '__main__':
    ApiAmniotic.launch()
