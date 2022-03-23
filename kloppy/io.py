import logging
import os
import urllib.parse
from typing import Union, IO, BinaryIO, Tuple

from io import BytesIO

from kloppy.config import get_config
from kloppy.exceptions import InputNotFoundError
from kloppy.infra.io.adapters import get_adapter


logger = logging.getLogger(__name__)

_open = open


FileLike = Union[str, bytes, IO[bytes]]


def get_local_cache_stream(url: str, cache_dir: str) -> Tuple[BinaryIO, bool]:
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    filename = urllib.parse.quote_plus(url)
    local_filename = f"{cache_dir}/{filename}"

    # Open the file in append+read mode
    # this makes sure:
    # 1. The file is created when it does not exist
    # 2. The file is not truncated when it does exist
    # 3. The file can be read
    return _open(local_filename, "a+b"), (
        os.path.exists(local_filename)
        and os.path.getsize(local_filename) > 0
        and local_filename
    )


def open_as_file(input_: FileLike) -> IO:
    if isinstance(input_, str):
        if "{" in input_ or "<" in input_:
            return BytesIO(input_.encode("utf8"))
        else:
            adapter = get_adapter(input_)
            if adapter:
                cache_dir = get_config("cache")
                if cache_dir:
                    stream, local_cache_file = get_local_cache_stream(
                        input_, cache_dir
                    )
                else:
                    stream = BytesIO()
                    local_cache_file = None

                if not local_cache_file:
                    logger.info(f"Retrieving {input_}")
                    adapter.read_to_stream(input_, stream)
                    logger.info("Retrieval complete")
                else:
                    logger.info(f"Using local cached file {local_cache_file}")
                stream.seek(0)
            else:
                if not os.path.exists(input_):
                    raise InputNotFoundError(f"File {input_} does not exist")

                stream = _open(input_, "rb")
            return stream
    elif isinstance(input_, bytes):
        return BytesIO(input_)
    else:
        return input_
