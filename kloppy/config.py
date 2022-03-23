import os
from contextlib import contextmanager
from copy import copy
from typing import Any, Optional

try:
    from typing import TypedDict
except ImportError:
    from mypy_extensions import TypedDict


cache_dir = os.environ.get("KLOPPY_CACHE_DIR")
if not cache_dir:
    cache_dir = os.path.expanduser("~/kloppy_cache")

Config = TypedDict(
    "Config",
    {
        "cache": Optional[str],
        "coordinate_system": Optional[str],
        "adapters.http.basic_authentication": Optional[str],
        "adapters.s3.s3fs": Optional[Any],
    },
)


class PartialConfig(Config, total=False):
    pass


_default_config: Config = {
    "cache": cache_dir,
    "coordinate_system": "kloppy",
    "adapters.http.basic_authentication": None,
    "adapters.s3.s3fs": None,
}

config = copy(_default_config)


def reset_config():
    for key, value in _default_config.items():
        set_config(key, value)


def set_config(key: str, value: Optional[str]):
    if key in config:
        config[key] = value
    else:
        raise KeyError(f"Non existing config '{key}'")


def get_config(key: Optional[str] = None):
    if key is None:
        return config
    elif key in config:
        return config[key]
    else:
        raise KeyError(f"Non existing config '{key}'")


@contextmanager
def config_context(*args):
    """Set some config items for within a certain context. Code borrowed partly from
    pandas."""
    if len(args) % 2 != 0 or len(args) < 2:
        raise ValueError(
            "Need to invoke as config_context(key, value, [(key, value), ...])."
        )

    configs = list(zip(args[::2], args[1::2]))

    undo = {key: get_config(key) for key, _ in configs}
    try:
        for key, value in configs:
            set_config(key, value)

        yield

    finally:
        for key, value in undo.items():
            set_config(key, value)
