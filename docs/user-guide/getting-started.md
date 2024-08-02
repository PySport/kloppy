# Getting started

!!! example

    This page should contain a 15-min tutorial that introduces the key
    concepts, tools and operations supported by kloppy. Along the way it will
    give pointers to much more detailed information.

This chapter is here to help you get started with kloppy. It covers all the fundamental features and functionalities of the library, making it easy for new users to familiarise themselves with the basics from initial installation and setup to core functionalities. If you're already familiar with kloppy's features, feel free to skip ahead to the [next chapter about installation options](installation.md).

## Installing kloppy

```bash
pip install kloppy
```

## Loading data

```python exec="true" source="above" session="getting-started/reading"
from kloppy import statsbomb

dataset = statsbomb.load_open_data(event_types=["pass", "shot"])
```

```python exec="true" result="text" session="getting-started/reading"
print(dataset.records[0])
print(dataset.to_df().head().to_markdown())
```

```python exec="on" result="text" session="getting-started/reading"
--8<-- "python/user-guide/getting-started/reading-writing.py:csv"
```
