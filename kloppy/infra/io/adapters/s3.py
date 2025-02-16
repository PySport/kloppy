import fsspec

from kloppy.config import get_config
from kloppy.exceptions import AdapterError

from .fsspec import FSSpecAdapter


class S3Adapter(FSSpecAdapter):
    def supports(self, url: str) -> bool:
        return url.startswith("s3://")

    def _get_filesystem(
        self, url: str, no_cache: bool = False
    ) -> fsspec.AbstractFileSystem:
        try:
            import s3fs
        except ImportError:
            raise AdapterError(
                "Seems like you don't have s3fs installed. Please"
                " install it using: pip install s3fs"
            )

        s3_fs = get_config("adapters.s3.s3fs") or s3fs.S3FileSystem()

        if no_cache:
            return s3_fs
        return fsspec.filesystem(
            "simplecache",
            fs=s3_fs,
            cache_storage=get_config("cache"),
        )
