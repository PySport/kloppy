from typing import List

import fsspec

from kloppy.config import get_config
from kloppy.exceptions import AdapterError

from .fsspec import FSSpecAdapter


def removeprefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


class ZipAdapter(FSSpecAdapter):
    def supports(self, url: str) -> bool:
        return url.startswith("zip://")

    def _get_filesystem(
        self, url: str, no_cache: bool = False
    ) -> fsspec.AbstractFileSystem:
        fo = get_config("adapters.zip.fo")
        if fo is None:
            raise AdapterError(
                "No zip archive provided for the zip adapter."
                " Please provide one using the 'adapters.zip.fo' config."
            )
        return fsspec.filesystem(
            protocol="zip",
            fo=fo,
        )

    def list_directory(self, url: str, recursive: bool = True) -> List[str]:
        """
        Lists the contents of a directory.
        """
        protocol = self._infer_protocol(url)
        fs = self._get_filesystem(url)
        url = removeprefix(url, "zip://")
        if recursive:
            files = fs.find(url, detail=False)
        else:
            files = fs.listdir(url, detail=False)
        return [
            f"{protocol}://{fp}"
            if protocol != "file" and not fp.startswith(protocol)
            else fp
            for fp in files
        ]
