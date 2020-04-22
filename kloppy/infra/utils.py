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
def performance_logging(description: str, counter: int = None):
    start = time.time()
    try:
        yield
    finally:
        took = (time.time() - start) * 1000
        if counter is not None:
            description += f" {counter / took}cycles/ms"
        print(f"Took: {took}ms: {description}")


