from contextlib import contextmanager
from logging import Logger
import time
from typing import Optional


@contextmanager
def performance_logging(
    description: str,
    counter: Optional[int] = None,
    logger: Optional[Logger] = None,
):
    start = time.time()
    try:
        yield
    finally:
        took = (time.time() - start) * 1000
        extra = ""
        if counter is not None:
            extra = f" ({counter / took * 1000:.1f}items/sec)"

        unit = "ms"
        if took < 0.1:
            took *= 1000
            unit = "us"

        msg = f"{description} took: {took:.2f}{unit} {extra}"
        if logger:
            logger.info(msg)
        else:
            print(msg)
