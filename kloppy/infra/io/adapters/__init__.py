from typing import Optional

from .adapter import Adapter
from .file import FileAdapter
from .http import HTTPAdapter
from .s3 import S3Adapter
from .zip import ZipAdapter

adapters = [FileAdapter(), HTTPAdapter(), S3Adapter(), ZipAdapter()]


def get_adapter(url: str) -> Optional[Adapter]:
    for adapter in adapters:
        if adapter.supports(url):
            return adapter
