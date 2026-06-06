import os

import fsspec

from .fsspec import FSSpecAdapter


class FileAdapter(FSSpecAdapter):
    def supports(self, url: str) -> bool:
        return self._infer_protocol(url) == "file"

    def _get_filesystem(
        self, url: str, no_cache: bool = False
    ) -> fsspec.AbstractFileSystem:
        return fsspec.filesystem("file")

    def list_directory(self, url: str, recursive: bool = True) -> list[str]:
        """
        Lists the contents of a directory.
        """
        fs = self._get_filesystem(url)
        if recursive:
            files = fs.find(url, detail=False)
        else:
            files = fs.listdir(url, detail=False)
        return [os.path.normpath(fp) for fp in files]
