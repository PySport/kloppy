import os

cache_dir = os.environ.get("KLOPPY_CACHE_DIR")
if not cache_dir:
    cache_dir = os.path.expanduser("~/kloppy_cache")

config = {
    "io.cache": cache_dir,
    "io.adapters.http.basic_authentication": None,
    "io.adapters.s3.s3fs": None,
    "deserializer.coordinate_system": "kloppy",
}


def set_config(key: str, value):
    if key in config:
        config[key] = value
    else:
        raise KeyError(f"Non existing config '{key}'")


def get_config(key: str):
    if key in config:
        return config[key]
    else:
        raise KeyError(f"Non existing config '{key}'")
