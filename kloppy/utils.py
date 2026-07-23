from contextlib import contextmanager
import functools
import importlib
import inspect
from io import BytesIO
from logging import Logger
import re
import sys
import time
import types
from typing import BinaryIO, Optional, Union
from urllib.parse import quote
from urllib.request import Request, urlopen
import warnings

Readable = Union[bytes, BinaryIO]


def to_file_object(s: Readable) -> BinaryIO:
    if isinstance(s, bytes):
        return BytesIO(s)
    return s


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


string_types = (bytes, str)


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


class DeprecatedEnumValue:
    def __init__(self, value):
        self.value = value

    def __get__(self, instance, owner):
        warnings.warn(
            f"{owner.__name__} is deprecated. Use GoalkeeperActionType instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.value


def snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    return re.sub(r"[\s\-]+", "_", s.strip()).lower()


def github_resolve_raw_data_url(repository: str, branch: str, file: str) -> str:
    """
    Resolve a GitHub repository file to its actual raw data URL.

    GitHub serves files differently depending on their size:
    - Small files are redirected to raw.githubusercontent.com
    - Large files (Git LFS) are redirected to media.githubusercontent.com

    This function follows the redirect and returns the final URL.

    Args:
        repository: The repository in the format "owner/repo" (e.g., "metrica-sports/sample-data")
        branch: The branch name (e.g., "master", "main")
        file: The file path within the repository (e.g., "data/file.csv")

    Returns:
        The resolved raw data URL

    Examples:
        >>> github_resolve_raw_data_url(
        ...     repository="metrica-sports/sample-data",
        ...     branch="master",
        ...     file="data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv"
        ... )
        'https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv'
    """
    # Encode the file path properly to handle spaces and special characters
    encoded_file = "/".join(quote(part, safe="") for part in file.split("/"))

    # Construct the GitHub raw URL
    # This URL will redirect to either raw.githubusercontent.com or media.githubusercontent.com
    github_url = f"https://github.com/{repository}/raw/refs/heads/{branch}/{encoded_file}"

    # Make a HEAD request to follow redirects and get the final URL
    req = Request(github_url, method="HEAD")
    try:
        with urlopen(req) as response:
            # The final URL after following redirects
            return response.url
    except Exception:
        # If there's an error, fall back to the standard raw.githubusercontent.com URL
        # This ensures backwards compatibility
        return f"https://raw.githubusercontent.com/{repository}/{branch}/{encoded_file}"


VERSIONS = {
    "networkx": "2.4",
    "pandas": "2.0.3",
    "polars": "0.16.6",
    "pyarrow": "17.0.0",
}

INSTALL_MAPPING = {
    "networkx": "networkx",
    "pandas": "pandas",
    "polars": "polars",
    "pyarrow": "pyarrow",
}


def _get_version(module: types.ModuleType) -> str:
    version = getattr(module, "__version__", None)
    if version is None:
        # xlrd uses a capitalized attribute name
        version = getattr(module, "__VERSION__", None)

    if version is None:
        raise ImportError(f"Can't determine version for {module.__name__}")
    return version


def import_optional_dependency(
    name: str,
    extra: str = "",
    raise_on_missing: bool = True,
    on_version: str = "raise",
    min_version: Optional[str] = None,
):
    """
    Import an optional dependency.

    By default, if a dependency is missing an ImportError with a nice
    message will be raised. If a dependency is present, but too old,
    we raise.

    Parameters
    ----------
    name : str
        The module name.
    extra : str
        Additional text to include in the ImportError message.
    raise_on_missing : bool, default True
        Whether to raise if the optional dependency is not found.
        When False and the module is not present, None is returned.
    on_version : str {'raise', 'warn'}
        What to do when a dependency's version is too old.

        * raise : Raise an ImportError
        * warn : Warn that the version is too old. Returns None
        * ignore: Return the module, even if the version is too old.
    min_version : str, default None
        Specify a minimum version that is different from the global kloppy
        minimum version required.
    Returns
    -------
    maybe_module : Optional[ModuleType]
        The imported module, when found and the version is correct.
        None is returned when the package is not found and `raise_on_missing`
        is False, or when the package's version is too old and `on_version`
        is ``'warn'``.
    """

    package_name = INSTALL_MAPPING.get(name)
    install_name = package_name if package_name is not None else name

    msg = (
        f"Missing optional dependency '{install_name}'. {extra} "
        f"Use pip or conda to install {install_name}."
    )
    try:
        module = importlib.import_module(name)
    except ImportError:
        if raise_on_missing:
            raise ImportError(msg) from None
        else:
            return None

    # Handle submodules: if we have submodule, grab parent module from sys.modules
    parent = name.split(".")[0]
    if parent != name:
        install_name = parent
        module_to_get = sys.modules[install_name]
    else:
        module_to_get = module
    minimum_version = (
        min_version if min_version is not None else VERSIONS.get(parent)
    )
    if minimum_version:
        version = _get_version(module_to_get)

        try:
            from packaging.version import parse as parse_version
        except ImportError:
            try:
                from distutils.version import LooseVersion as parse_version
            except ImportError:

                def parse_version(v):
                    return tuple(map(int, (v.split(".") + ["0", "0"])[:3]))

        if parse_version(version) < parse_version(minimum_version):
            assert on_version in {"warn", "raise", "ignore"}
            msg = (
                f"Kloppy requires version '{minimum_version}' or newer of '{parent}' "
                f"(version '{version}' currently installed)."
            )
            if on_version == "warn":
                warnings.warn(msg, UserWarning)
                return None
            elif on_version == "raise":
                raise ImportError(msg)

    return module
