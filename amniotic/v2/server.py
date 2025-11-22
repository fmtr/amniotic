import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from amniotic.paths import paths
from amniotic.v2.sandbox_ffmpy import Recording, Theme


class ApiBase:
    TITLE = 'Base API'
    HOST = '0.0.0.0'
    PORT = 8080

    def add_endpoint(self, method, path, tags=None, method_http=None):

        method_http = method_http or self.app.post

        if type(tags) is str:
            tags = [tags]

        doc = (method.__doc__ or '').strip() or None

        method_http(
            path,
            tags=tags,
            description=doc,
            summary=doc

        )(method)

    def __init__(self):

        self.app = FastAPI(title=self.TITLE)

        for config in self.get_endpoints():
            self.add_endpoint(**config)

    def get_endpoints(self):

        endpoints = [

        ]

        return endpoints

    @classmethod
    def launch(cls):
        self = cls()
        import uvicorn
        logging.info(f'Launching API {cls.TITLE}...')
        uvicorn.run(self.app, host=self.HOST, port=self.PORT)


class ApiAm(ApiBase):
    TITLE = 'Amniotic Test API'

    def __init__(self):
        super().__init__()
        self.themes = []

    def get_endpoints(self):
        endpoints = [
            dict(method_http=self.app.get, path='/stream', method=self.stream),
            dict(path='/vol', method=self.vol),
            dict(path='/add', method=self.add)
        ]

        return endpoints

    async def vol(self, rec_id: int, volume: float):
        self.themes[0].recordings[rec_id].volume = volume
        volume

    async def add(self, name: str):
        rec = Recording(f'/artifacts/audio/{name}', volume=.9)
        self.themes[0].recordings.append(rec)

    async def stream(self):
        recs = [
            Recording(paths.example_700KB, volume=.3),

        ]

        theme = Theme(recs)

        self.themes.append(theme)

        response = StreamingResponse(theme, media_type="audio/mpeg")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Connection"] = "close"  # Close the connection when done

        return response


if __name__ == '__main__':
    ApiAm.launch()
