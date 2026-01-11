from fmtr.tools import http


class ClientHA(http.Client):
    @property
    def url_api(self):
        from amniotic.settings import settings

        return f"{settings.ha_core_api}"

    @property
    def headers_auth(self):
        from amniotic.settings import settings
        return {"Authorization": f"Bearer {settings.token}"}


client_ha = ClientHA()
