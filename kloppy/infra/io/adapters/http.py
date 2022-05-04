from typing import BinaryIO
import base64

from kloppy.config import get_config
from kloppy.exceptions import AdapterError
from .adapter import Adapter


class HTTPAdapter(Adapter):
    def supports(self, url: str) -> bool:
        return url.startswith("http://") or url.startswith("https://")

    def read_to_stream(self, url: str, output: BinaryIO):
        basic_authentication = get_config("adapters.http.basic_authentication")

        try:
            from js import XMLHttpRequest

            _RUNS_IN_BROWSER = True
        except ImportError:
            try:
                import requests
            except ImportError:
                raise AdapterError(
                    "Seems like you don't have requests installed. Please"
                    " install it using: pip install requests"
                )

            _RUNS_IN_BROWSER = False

        if _RUNS_IN_BROWSER:
            request = XMLHttpRequest.new()
            if basic_authentication:
                authentication = base64.b64encode(
                    basic_authentication.join(":")
                )
                request.setRequestHeader(
                    "Authorization",
                    f"Basic {authentication}",
                )

            request.open("GET", url, False)
            request.send(None)
            output.write(request.responseText)
        else:
            auth = None
            if basic_authentication:
                auth = requests.auth.HTTPBasicAuth(*basic_authentication)

            with requests.get(url, stream=True, auth=auth) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    output.write(chunk)
