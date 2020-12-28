import re
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


_first_cap_re = re.compile("(.)([A-Z][a-z0-9]+)")
_all_cap_re = re.compile("([a-z0-9])([A-Z])")


def camelcase_to_snakecase(name: str) -> str:
    """Convert camel-case string to snake-case."""
    s1 = _first_cap_re.sub(r"\1_\2", name)
    return _all_cap_re.sub(r"\1_\2", s1).lower()


def removes_suffix(string: str, suffix: str) -> str:
    if string[-len(suffix) :] == suffix:
        return string[: -len(suffix)]
    else:
        return string


def docstring_inherit_attributes(parent):
    def inherit(obj):
        other_docs, attribute_docs = obj.__doc__.split("Attributes:\n")

        own_attributes = [
            attribute.strip()
            for attribute in attribute_docs.strip().split("\n")
        ]

        parent_attributes = [
            attribute.strip()
            for attribute in parent.__doc__.split("Attributes:\n")[-1]
            .strip()
            .split("\n")
        ]
        obj.__doc__ = (
            other_docs
            + "Attributes:\n        "
            + "\n        ".join(parent_attributes)
            + "\n        "
            + "\n        ".join(own_attributes)
            + "\n"
        )
        return obj

    return inherit
