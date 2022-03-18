from typing import Optional

from .adapter import Adapter
from .http import HTTPAdapter
from .s3 import S3Adapter

_adapters = [HTTPAdapter()]


def get_adapter(url: str) -> Optional[Adapter]:
    for adapter in _adapters:
        if adapter.supports(url):
            return adapter
