"""I/O utilities for reading raw data."""
import contextlib
import logging
import os
import urllib.parse
from dataclasses import dataclass, replace
from io import BytesIO, BufferedIOBase
from pathlib import PurePath
from typing import (
    IO,
    BinaryIO,
    Tuple,
    Union,
    Optional,
    Generator,
    ContextManager,
)

from kloppy.config import get_config
from kloppy.exceptions import InputNotFoundError
from kloppy.infra.io.adapters import get_adapter

logger = logging.getLogger(__name__)


def _open(file: str, mode: str) -> IO:
    if file.endswith(".gz"):
        import gzip

        return gzip.open(file, mode)
    elif file.endswith(".xz"):
        import lzma

        return lzma.open(file, mode)
    elif file.endswith(".bz2"):
        import bz2

        return bz2.open(file, mode)
    return open(file, mode)


def _decompress(stream: BinaryIO) -> BinaryIO:
    stream.seek(0)
    if stream.read(3) == b"\x1f\x8b\x08":
        import gzip

        stream.seek(0)
        print("GZIP")
        return gzip.GzipFile(fileobj=stream, mode="rb")
    elif stream.read(6) == b"\xfd7zXZ\x00":
        import lzma

        stream.seek(0)
        return lzma.LZMAFile(stream)
    elif stream.read(3) == b"BZh":
        import bz2

        stream.seek(0)
        return bz2.BZ2File(stream)
    stream.seek(0)
    return stream


@dataclass(frozen=True)
class Source:
    """A wrapper around a file-like object to enable optional inputs.

    Args:
        data (FileLike): The file-like object.
        optional (bool): Whether the file is optional. Defaults to False.
        skip_if_missing (bool): Whether to skip the file if it is missing. Defaults to False.

    Example:
        >>> open_as_file(Source.create("example.csv", optional=True))
    """

    data: "FileLike"
    optional: bool = False
    skip_if_missing: bool = False

    @classmethod
    def create(cls, input_: "FileLike", **kwargs):
        if isinstance(input_, Source):
            return replace(input_, **kwargs)
        return Source(data=input_, **kwargs)


FileLike = Union[str, PurePath, bytes, BinaryIO, Source]


def get_file_extension(f: FileLike) -> str:
    """Determine the file extension of the given file-like object.

    Args:
        f (FileLike): The file-like object whose extension needs to be determined.

    Returns:
        str: The file extension, including the dot ('.') if present.

    Raises:
        Exception: If the extension cannot be determined.

    Note:
        - If the file has compression extensions such as '.gz', '.xz', or
          '.bz2', they will be stripped before determining the extension.

    Example:
        >>> get_file_extension("example.xml.gz")
        '.xml'
        >>> get_file_extension(Path("example.txt"))
        '.txt'
        >>> get_file_extension(Source(data="example.csv"))
        '.csv'
    """
    if isinstance(f, PurePath) or isinstance(f, str):
        f = str(f)
        for ext in [".gz", ".xz", ".bz2"]:
            if f.endswith(ext):
                f = f[: -len(ext)]
        return os.path.splitext(f)[1]
    elif isinstance(f, Source):
        return get_file_extension(f.data)
    else:
        raise Exception("Could not determine extension")


def get_local_cache_stream(
    url: str, cache_dir: str
) -> Tuple[BinaryIO, Union[bool, str]]:
    """Get a stream to the local cache file for the given URL.

    Args:
        url (str): The URL to cache.
        cache_dir (str): The directory where the cache file will be stored.

    Returns:
        Tuple[BinaryIO, bool | str]: A tuple containing a binary stream to the
        local cache file and the path to the cache file if it already
        exists and is non-empty, otherwise False.

    Note:
        - If the specified cache directory does not exist, it will be created.
        - If the cache file  does not exist, it will be created and will be
          named after the URL.

    Example:
        >>> stream, exists = get_local_cache_stream("https://example.com/data", "./cache")
    """
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    filename = urllib.parse.quote_plus(url)
    local_filename = f"{cache_dir}/{filename}"

    # Open the file in append+read mode
    # this makes sure:
    # 1. The file is created when it does not exist
    # 2. The file is not truncated when it does exist
    # 3. The file can be read
    return open(local_filename, "a+b"), (
        os.path.exists(local_filename)
        and os.path.getsize(local_filename) > 0
        and local_filename
    )


@contextlib.contextmanager
def dummy_context_mgr() -> Generator[None, None, None]:
    yield


def open_as_file(input_: FileLike) -> ContextManager[Optional[BinaryIO]]:
    """Open a byte stream to the given input object.

    The following input types are supported:
        - A string or `pathlib.Path` object representing a local file path.
        - A string representing a URL. It should start with 'http://' or
          'https://'.
        - A string representing a path to a file in a Amazon S3 cloud storage
          bucket. It should start with 's3://'.
        - A xml or json string containing the data. The string should contain
          a '{' or '<' character. Otherwise, it will be treated as a file path.
        - A bytes object containing the data.
        - A buffered binary stream that inherits from `io.BufferedIOBase`.
        - A [Source](`kloppy.io.Source`) object that wraps any of the above
          input types.

    Args:
        input_ (FileLike): The input object to be opened.

    Returns:
        BinaryIO: A binary stream to the input object.

    Raises:
        InputNotFoundError: If the input file is not found.

    Example:
        >>> with open_as_file("example.txt") as f:
        ...     contents = f.read()

    Note:
        To support reading data from other sources, see the
        [Adapter](`kloppy.io.adapters.Adapter`) class.

        If the given file path or URL ends with '.gz', '.xz', or '.bz2', the
        file will be decompressed before being read.
    """
    if isinstance(input_, Source):
        if input_.data is None and input_.optional:
            # This saves us some additional code in every vendor specific code
            return dummy_context_mgr()

        try:
            return open_as_file(input_.data)
        except InputNotFoundError:
            if input_.skip_if_missing:
                logging.info(f"Input {input_.data} not found. Skipping")
                return dummy_context_mgr()
            raise
    elif isinstance(input_, str) and ("{" in input_ or "<" in input_):
        return BytesIO(input_.encode("utf8"))
    elif isinstance(input_, bytes):
        return BytesIO(input_)
    elif isinstance(input_, str) or isinstance(input_, PurePath):
        if isinstance(input_, PurePath):
            input_ = str(input_)

        adapter = get_adapter(input_)
        if adapter:
            cache_dir = get_config("cache")
            assert cache_dir is None or isinstance(cache_dir, str)
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
            stream = _decompress(stream)
        else:
            if not os.path.exists(input_):
                raise InputNotFoundError(f"File {input_} does not exist")

            stream = _open(input_, "rb")
        return stream
    elif isinstance(input_, BufferedIOBase):
        return input_

    raise ValueError(f"Unsupported input type: {type(input_)}")
