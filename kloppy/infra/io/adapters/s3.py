import shutil
from typing import BinaryIO

from kloppy.config import get_config
from kloppy.exceptions import AdapterError
from .adapter import Adapter


class S3Adapter(Adapter):
    def supports(self, url: str) -> bool:
        return url.startswith("s3://")

    def read_to_stream(self, url: str, output: BinaryIO):
        try:
            import s3fs
        except ImportError:
            raise AdapterError(
                "Seems like you don't have s3fs installed. Please"
                " install it using: pip install s3fs"
            )

        s3_fs = get_config("io.adapters.s3.s3fs")
        if not s3_fs:
            s3_fs = s3fs.S3FileSystem()

        with s3_fs.open(url, "rb") as fp:
            shutil.copyfile(fp, output)
