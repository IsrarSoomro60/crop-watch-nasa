"""HTTP session that signs in to NASA Earthdata Login (URS) when a data archive redirects there.

NASA archives such as GES DISC (GPM) and PO.DAAC (GRACE) redirect requests to
urs.earthdata.nasa.gov. Redirects are followed by hand so the credentials are sent
only to that host (httpx drops auth on cross-host redirects, and must, for safety).
Session cookies set by the archive are kept for later requests. Credentials come from
backend/.env (EARTHDATA_USERNAME / EARTHDATA_PASSWORD) and are never logged.
"""

import httpx

from app.core.config import Settings

URS_HOST = "urs.earthdata.nasa.gov"
MAX_REDIRECTS = 10


class EarthdataNotConfigured(RuntimeError):
    pass


class EarthdataSession:
    def __init__(self, settings: Settings, timeout: float = 120.0, transport: httpx.BaseTransport | None = None):
        if not settings.earthdata_username or not settings.earthdata_password:
            raise EarthdataNotConfigured("Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD in backend/.env")
        self._auth = httpx.BasicAuth(settings.earthdata_username, settings.earthdata_password)
        self._client = httpx.Client(follow_redirects=False, timeout=timeout, transport=transport)

    def get(self, url: str) -> httpx.Response:
        for _ in range(MAX_REDIRECTS):
            target = httpx.URL(url)
            response = self._client.get(target, auth=self._auth if target.host == URS_HOST else None)
            if not response.is_redirect:
                return response
            url = str(response.next_request.url) if response.next_request else response.headers["location"]
        raise httpx.TooManyRedirects(f"More than {MAX_REDIRECTS} redirects", request=response.request)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EarthdataSession":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
