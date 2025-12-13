import fsspec

from .fsspec import FSSpecAdapter


class FileAdapter(FSSpecAdapter):
    def supports(self, url: str) -> bool:
        return self._infer_protocol(url) == "file"

    def _get_filesystem(
        self, url: str, no_cache: bool = False
    ) -> fsspec.AbstractFileSystem:
        return fsspec.filesystem("file")
