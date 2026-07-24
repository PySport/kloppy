import importlib
import sys
import types
from typing import Optional
import warnings

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
    "s3fs": "s3fs",
}


def _get_version(module: types.ModuleType) -> str:
    """Get the version string from a module.

    Args:
        module (types.ModuleType): The module to check for a version.

    Returns:
        str: The version string of the module.

    Raises:
        ImportError: If the version cannot be determined.
    """
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
    """Import an optional dependency.

    By default, if a dependency is missing an ImportError with a nice
    message will be raised. If a dependency is present, but too old,
    we raise.

    Args:
        name (str): The module name.
        extra (str, optional): Additional text to include in the ImportError message.
            Defaults to "".
        raise_on_missing (bool, optional): Whether to raise if the optional dependency
            is not found. When False and the module is not present, None is returned.
            Defaults to True.
        on_version (str, optional): What to do when a dependency's version is too old.
            - 'raise': Raise an ImportError.
            - 'warn': Warn that the version is too old. Returns None.
            - 'ignore': Return the module, even if the version is too old.
            Defaults to "raise".
        min_version (str, optional): Specify a minimum version that is different from
            the global kloppy minimum version required. Defaults to None.

    Returns:
        Optional[types.ModuleType]: The imported module, when found and the version
            is correct. None is returned when the package is not found and
            `raise_on_missing` is False, or when the package's version is too old and
            `on_version` is 'warn'.
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
