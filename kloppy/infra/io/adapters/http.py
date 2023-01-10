from typing import BinaryIO

from kloppy.config import get_config
from kloppy.exceptions import AdapterError, InputNotFoundError
from .adapter import Adapter

try:
    from js import XMLHttpRequest

    RUNS_IN_BROWSER = True
except ImportError:
    RUNS_IN_BROWSER = False


def check_requests_patch():
    if RUNS_IN_BROWSER:
        try:
            import pyodide_http
        except ImportError:
            raise AdapterError(
                "Seems like you don't have `pyodide-http` installed, which is required to make http requests "
                "work in the browser. Please install it using: pip install pyodide-http"
            )

        pyodide_http.patch_all()


class HTTPAdapter(Adapter):
    def supports(self, url: str) -> bool:
        return url.startswith("http://") or url.startswith("https://")

    def read_to_stream(self, url: str, output: BinaryIO):
        check_requests_patch()

        basic_authentication = get_config("adapters.http.basic_authentication")

        try:
            import requests
        except ImportError:
            raise AdapterError(
                "Seems like you don't have `requests` installed. Please"
                " install it using: pip install requests"
            )

        auth = None
        if basic_authentication:
            auth = requests.auth.HTTPBasicAuth(*basic_authentication)

        with requests.get(url, stream=True, auth=auth) as r:
            if r.status_code == 404:
                raise InputNotFoundError(f"Could not find {url}")

            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                output.write(chunk)
