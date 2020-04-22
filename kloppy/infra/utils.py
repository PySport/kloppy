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
        took = int((time.time() - start) * 1000)
        extra = ""
        if counter is not None:
            extra = f" ({int(counter / took * 1000)}items/sec)"
        print(f"{description} took: {took:.2f}ms {extra}")


