# Config

Kloppy has an API to configure and customize global behavior related to setting the default coordinate system for all load calls, setting the cache directory (or disabling the cache) and passing settings to adapters.

The API is composed of 3 functions, available from the `kloppy.config` namespace:

```python exec="true" source="above" session="config"
from kloppy.config import get_config, set_config, config_context
```

- [`get_config()`][kloppy.config.get_config] - get the value of a single option.
- [`set_config()`][kloppy.config.set_config] - set the value of a single option.
- [`config_context()`][kloppy.config.config_context] - execute a codeblock with a set of options that revert to prior settings after execution.

## Get config

You can get all configuration variables or just a single one using [`get_config()`][kloppy.config.get_config].

```pycon exec="true" source="console" session="config"
>>> cfg = get_config()
>>> print(cfg)
```

To get a single configuration variable, you must pass the name of the variable as an argument.

```pycon exec="true" source="console" session="config"
>>> cfg_coordinate_system = get_config("coordinate_system")
>>> print(cfg_coordinate_system)
```


## Set config
Using [`set_config()`][kloppy.config.set_config] you can set the value for a single config variable. This value will be used for all calls to kloppy.

```pycon exec="true" source="console" session="config"
>>> from kloppy import statsbomb

>>> set_config("coordinate_system", "opta")

>>> dataset = statsbomb.load_open_data()
>>> print(dataset.metadata.coordinate_system)
```


## Config context

Inspired by pandas, kloppy allows you to set config variables for a context (using a context manager). Config set using [`config_context()`][kloppy.config.config_context] will be reverted to the original values when python exits the context.

```pycon exec="true" source="console" session="config"
>>> print(f"Before context: {get_config('coordinate_system')}")
>>> with config_context("coordinate_system", "statsbomb"):
>>>     print(f"Within context: {get_config('coordinate_system')}")
>>>     dataset = statsbomb.load_open_data()

>>> print(f"After context: {get_config('coordinate_system')}")
>>> print(dataset.metadata.coordinate_system)
```


```python exec="true" session="config"
set_config("coordinate_system", "kloppy")
```

