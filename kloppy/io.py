import logging
import os
import urllib.parse
from typing import Union, IO, Dict

from io import BytesIO

import requests


logger = logging.getLogger(__name__)

_open = open


FileLike = Union[str, bytes, IO[bytes]]


def download_file(url: str, local_filename: str) -> None:
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def get_local_file(url: str) -> str:
    cache_dir = os.environ.get("KLOPPY_CACHE_DIR", None)
    if not cache_dir:
        cache_dir = os.path.expanduser("~/kloppy_cache")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    filename = urllib.parse.quote_plus(url)
    local_filename = f"{cache_dir}/{filename}"
    if not os.path.exists(local_filename):
        logger.info(f"Downloading {filename}")
        download_file(url, local_filename)
        logger.info("Download complete")
    else:
        logger.info(f"Using local cached file {local_filename}")
    return local_filename


def open_as_file(input_: FileLike) -> IO:
    if isinstance(input_, str):
        if "{" in input_ or "<" in input_:
            return BytesIO(input_.encode("utf8"))
        else:
            if input_.startswith("http://") or input_.startswith("https://"):
                input_ = get_local_file(input_)

            return _open(input_, "rb")
    elif isinstance(input_, bytes):
        return BytesIO(input_)
    else:
        return input_
