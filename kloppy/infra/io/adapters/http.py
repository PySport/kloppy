from typing import BinaryIO, List

import fsspec

from kloppy.config import get_config
from kloppy.exceptions import AdapterError, InputNotFoundError

from .adapter import Adapter
from .fsspec import FSSpecAdapter

try:
    from js import XMLHttpRequest  # noqa: F401

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


class HTTPAdapter(FSSpecAdapter):
    def supports(self, url: str) -> bool:
        return url.startswith("http://") or url.startswith("https://")

    def _get_filesystem(
        self, url: str, no_cache: bool = False
    ) -> fsspec.AbstractFileSystem:
        try:
            import aiohttp
        except ImportError:
            raise AdapterError(
                "Seems like you don't have `aiohttp` installed, which is required to authenticate. "
                "Please install it using: pip install aiohttp"
            )

        check_requests_patch()

        basic_authentication = get_config("adapters.http.basic_authentication")

        client_kwargs = {}
        if basic_authentication:
            client_kwargs["auth"] = aiohttp.BasicAuth(*basic_authentication)

        if no_cache:
            return fsspec.filesystem("http", client_kwargs=client_kwargs)
        else:
            return fsspec.filesystem(
                "simplecache",
                target_protocol="http",
                target_options={"client_kwargs": client_kwargs},
                cache_storage=get_config("cache"),
            )

    def is_directory(self, url: str) -> bool:
        """
        Check if the given URL points to a directory.
        """
        fs = self._get_filesystem(url, no_cache=True)
        return fs.isdir(url)
