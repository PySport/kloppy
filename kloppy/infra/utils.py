import time
from contextlib import contextmanager
from io import BytesIO
from typing import BinaryIO, Union

Readable = Union[bytes, BinaryIO]


def to_file_object(s: Readable) -> BinaryIO:
    if isinstance(s, bytes):
        return BytesIO(s)
    return s


@contextmanager
def performance_logging(description: str, counter: int = None, logger=None):
    start = time.time()
    try:
        yield
    finally:
        took = (time.time() - start) * 1000
        extra = ""
        if counter is not None:
            extra = f" ({int(counter / took * 1000)}items/sec)"

        unit = "ms"
        if took < 0.1:
            took *= 1000
            unit = "us"

        msg = f"{description} took: {took:.2f}{unit} {extra}"
        if logger:
            logger.info(msg)
        else:
            print(msg)
