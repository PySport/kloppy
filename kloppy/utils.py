import re
import time
from contextlib import contextmanager
from io import BytesIO
from typing import BinaryIO, Union
import functools
import inspect
import warnings


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


string_types = (type(b""), type(""))


def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    if isinstance(reason, string_types):
        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):
            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter("always", DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                warnings.simplefilter("default", DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):
        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))
