from fastapi.responses import StreamingResponse

from amniotic.paths import paths
from amniotic.v2.sandbox_ffmpy import Recording, Theme
from fmtr.tools import api


class ApiAm(api.Base):
    TITLE = 'Amniotic Test API'
    URL_DOCS = '/'

    def __init__(self):
        super().__init__()
        self.themes = []

    def get_endpoints(self):
        endpoints = [
            api.Endpoint(method_http=self.app.get, path='/stream', method=self.stream),
            api.Endpoint(path='/vol', method=self.vol),
            api.Endpoint(path='/add', method=self.add)
        ]

        return endpoints

    async def vol(self, rec_id: int, volume: float):
        self.themes[0].recordings[rec_id].volume = volume
        volume

    async def add(self, name: str):
        rec = Recording(paths.gambling, volume=.9)
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
