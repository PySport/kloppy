from typing import Optional

from .adapter import Adapter
from .http import HTTPAdapter
from .s3 import S3Adapter

adapters = [HTTPAdapter(), S3Adapter()]


def get_adapter(url: str) -> Optional[Adapter]:
    for adapter in adapters:
        if adapter.supports(url):
            return adapter
