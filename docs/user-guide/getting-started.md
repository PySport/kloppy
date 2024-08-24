# Getting started

!!! example

    This page should contain a 15-min tutorial that introduces the key
    concepts, tools and operations supported by kloppy. This includes
    loading event and tracking data, outputting the data to a dataframe,
    transforming the coordinate system, the metadata, and navigating a dataset.
    Along the way it will give pointers to much more detailed information.

This chapter is here to help you get started with kloppy. It covers all the fundamental features and functionalities of the library, making it easy for new users to familiarise themselves with the basics from initial installation and setup to core functionalities. If you're already familiar with kloppy's features, feel free to skip ahead to the [next chapter about installation options](installation.md).

## Installing kloppy

```bash
pip install kloppy
```

## Event stream data

```python exec="true" source="above" session="getting-started"
from kloppy import metrica

API_URL = "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data"

event_dataset = metrica.load_event(
    meta_data=f"{API_URL}/Sample_Game_3/Sample_Game_3_metadata.xml",
    event_data=f"{API_URL}/Sample_Game_3/Sample_Game_3_events.json",
    coordinates="metrica"
)
```

```python exec="true" result="text" session="getting-started"
print(event_dataset.records[0])
```

```python exec="true" result="text" session="getting-started"
print(event_dataset.to_df().head().to_markdown())
```

```python exec="on" result="text" session="getting-started"
--8<-- "python/user-guide/getting-started/reading-writing.py:csv"
```

## Tracking data

```python exec="true" source="above" session="getting-started"
from kloppy import metrica

API_URL = "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data"

# Load the raw data, we'll only load the first 30 seconds of the game
tracking_dataset = metrica.load_tracking_epts(
    meta_data=f"{API_URL}/Sample_Game_3/Sample_Game_3_metadata.xml",
    raw_data=f"{API_URL}/Sample_Game_3/Sample_Game_3_tracking.txt",
    limit=30*25,
    coordinates="metrica"
)
```
