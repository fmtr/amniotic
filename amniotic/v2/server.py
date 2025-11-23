import asyncio

import uvicorn
from fastapi.responses import StreamingResponse

from amniotic.v2.recording import ThemeDefinition
from fmtr.tools import api, mqtt


class ApiAm(api.Base):
    TITLE = 'Amniotic Test API'
    URL_DOCS = '/'

    def __init__(self):
        super().__init__()

        self.theme_test = ThemeDefinition('test')
        self.theme_defs = [self.theme_test]

    def get_endpoints(self):
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/stream', method=self.stream),
            api.Endpoint(path='/vol', method=self.vol),
            api.Endpoint(path='/enable', method=self.enable),
            api.Endpoint(path='/disable', method=self.disable)
        ]

        return endpoints

    async def vol(self, rec_id: int, volume: float):
        self.theme_defs[0].recordings[rec_id].volume = volume
        volume

    async def enable(self):
        defin = ThemeDefinition.DEFINITIONS[1]
        self.theme_test.enable(defin)

    async def disable(self):
        defin = ThemeDefinition.DEFINITIONS[1]
        self.theme_test.disable(defin)

    async def stream(self):
        defin = ThemeDefinition.DEFINITIONS[0]
        self.theme_test.enable(defin)
        stream = self.theme_test.get_stream()

        response = StreamingResponse(stream, media_type="audio/mpeg")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Connection"] = "close"  # Close the connection when done

        return response

    async def launch(self):
        config = uvicorn.Config(self.app, host=self.HOST, port=self.PORT)
        api = uvicorn.Server(config)
        await api.serve()

    @classmethod
    async def start(cls, client: mqtt.Client):
        self = cls()
        await asyncio.gather(
            self.launch(),
            client.start(),
        )

if __name__ == '__main__':
    ApiAm.launch()
