from typing import Optional

from .adapter import Adapter
from .http import HTTPAdapter
from .s3 import S3Adapter

adapters = {
    "http": HTTPAdapter(),
    "s3": S3Adapter()
}


def get_adapter(url: str) -> Optional[Adapter]:
    for adapter in adapters.values():
        if adapter.supports(url):
            return adapter
