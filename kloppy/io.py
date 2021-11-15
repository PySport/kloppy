from typing import Union, IO

from io import BytesIO

_open = open


FileLike = Union[str, bytes, IO[bytes]]


def open_as_file(path_or_str_or_io: FileLike) -> IO:
    if isinstance(path_or_str_or_io, str):
        if "{" in path_or_str_or_io or "<" in path_or_str_or_io:
            return BytesIO(path_or_str_or_io.encode("utf8"))
        else:
            return _open(path_or_str_or_io, "rb")
    elif isinstance(path_or_str_or_io, bytes):
        return BytesIO(path_or_str_or_io)
    else:
        return path_or_str_or_io
