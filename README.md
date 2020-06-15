# kloppy: standardizing soccer tracking- and event data
> klop·pen (klopte, heeft geklopt) - juist zijn; overeenkomen, uitkomen met: dat klopt, dat kan kloppen is juist; dat klopt als een zwerende vinger dat is helemaal juist

[![PyPI Latest Release](https://img.shields.io/pypi/v/kloppy.svg)](https://pypi.org/project/kloppy/)
[![Downloads](https://pepy.tech/badge/kloppy/month)](https://pepy.tech/project/kloppy/month)
![](https://img.shields.io/github/license/PySport/kloppy)
![](https://img.shields.io/pypi/pyversions/kloppy)
[![Powered by PySport](https://img.shields.io/badge/powered%20by-PySport-orange.svg?style=flat&colorA=104467&colorB=007D8A)](https://pysport.org)
--------
## What is it?

**kloppy** is a Python package providing (de)serializers for soccer tracking- and event data,
standardized data models, filters, and transformers designed to make working with 
different tracking- and event data like a breeze. It aims to be the fundamental building blocks for loading, filtering and tranforming
 tracking- and event data.

## Main Features
Here are just a few of the things that kloppy does well:
- Directly load [**Public datasets**](#datasets) to get started right away. 
- Understandable [**Standardized models**](#models) for tracking- and event datasets
- Out-of-the-box [**(De)serializing**](#serializing) tracking- and event data from different sources into standardized models and vice versa
- Flexible [**pitch dimensions**](#pitch-dimensions) transformer for changing a dataset pitch dimensions from one to another (eg OPTA's 100x100 -> TRACAB meters)
- Intelligent [**orientation**](#orientation) transforming orientation of a dataset (eg from TRACAB fixed orientation to "Home Team" orientation)


## Where to get it
The source code is currently hosted on GitHub at:
https://github.com/PySport/kloppy

Installers for the latest released version are available at the [Python
package index](https://pypi.org/project/kloppy).

```sh
# or PyPI
pip install kloppy
```

## Quickstart
We added some helper functions to get started really quickly. The helpers allow eay loading, transforming and converting to pandas of tracking data.
```python
from kloppy import (
    load_metrica_tracking_data, 
    load_tracab_tracking_data,
    load_epts_tracking_data, 
    load_statsbomb_event_data,
    to_pandas, 
    transform
)

# metrica data
dataset = load_metrica_tracking_data('home_file.csv', 'away_file.csv')
# or tracab
dataset = load_tracab_tracking_data('meta.xml', 'raw_data.txt')
# or epts
dataset = load_epts_tracking_data('meta.xml', 'raw_data.txt')

# or event data
dataset = load_statsbomb_event_data('event_data.json', 'lineup.json')


dataset = transform(dataset, pitch_dimensions=[[0, 108], [-34, 34]])
pandas_data_frame = to_pandas(dataset)
```

### <a name="datasets"></a>Public datasets / Very quick start
More and more companies are publishing (demo) datasets to get you started. Inspired by the `tensorflow_datasets` package,
we added a "dataset loader" which does all the heavy lifting for you: find urls, download files, organize and load them.
```python
from kloppy import datasets

dataset = datasets.load("metrica_tracking", options={'sample_rate': 1./12, 'limit': 10})
```

### <a name="models"></a>Standardized models
Most providers use different names for the same thing. This module tries to model the real world as much as possible.
Understandable models are important and in some cases this means performance is subordinate to models that are easy to 
reason about. Please browse to source of `domain.models` to find the available models.

### <a name="deserializing"></a>(De)serializing data
When working with tracking- or event data we need to deserialize it from the format the provider uses. **kloppy**
will provide both deserializing as serializing. This will make it possible to read format one, transform and filter and store
in a different format.

```python
from kloppy import TRACABSerializer

serializer = TRACABSerializer()

with open("tracab_data.dat", "rb") as raw, \
        open("tracab_metadata.xml", "rb") as meta:

    dataset = serializer.deserialize(
        inputs={
            'raw_data': raw,
            'meta_data': meta
        },
        options={
            "sample_rate": 1 / 12
        }
    )
    
    # start working with dataset
```

or Metrica data
```python
from kloppy import MetricaTrackingSerializer

serializer = MetricaTrackingSerializer()

with open("Sample_Game_1_RawTrackingData_Away_Team.csv", "rb") as raw_away, \
        open("Sample_Game_1_RawTrackingData_Home_Team.csv", "rb") as raw_home:

    dataset = serializer.deserialize(
        inputs={
            'raw_data_home': raw_home,
            'raw_data_away': raw_away
        },
        options={
            "sample_rate": 1 / 12
        }
    )
    
    # start working with dataset
```


or EPTS data
```python
from kloppy import EPTSSerializer

serializer = EPTSSerializer()

with open("raw_data.txt", "rb") as raw, \
        open("metadata.xml", "rb") as meta:

    dataset = serializer.deserialize(
        inputs={
            'raw_data': raw,
            'meta_data': meta
        },
        options={
            "sample_rate": 1 / 12
        }
    )
    
    # start working with dataset
```


or StatsBomb event data
```python
from kloppy import StatsBombSerializer

serializer = StatsBombSerializer()

with open("events/123123.json", "rb") as event_data, \
        open("lineup/123123.json", "rb") as lineup_data:

    dataset = serializer.deserialize(
        inputs={
            'event_data': event_data,
            'lineup_data': lineup_data
        },
        options={
            "event_types": ["pass", "shot", "carry", "take_on"]
        }
    )
    
    # start working with dataset
```



### <a name="pitch-dimensions"></a>Transform the pitch dimensions
Data providers use their own pitch dimensions. Some use actual meters while others use 100x100. Use the Transformer to get from one pitch dimensions to another one.
```python
from kloppy.domain import Transformer, PitchDimensions, Dimension

# use deserialized `dataset`
new_dataset = Transformer.transform_dataset(
    dataset,
    to_pitch_dimensions=PitchDimensions(
        x_dim=Dimension(0, 100),
        y_dim=Dimension(0, 100)
    )
)
```


### <a name="orientation"></a>Transform the orientation
Data providers can use different orientations. Some use a fixed orientation and others use ball owning team.


```python
from kloppy.domain import Transformer, Orientation

new_dataset = Transformer.transform_dataset(
    dataset,
    to_orientation=Orientation.BALL_OWNING_TEAM
)
```

### Transforming pitch dimensions and orientation at the same time
```python
from kloppy.domain import Transformer, PitchDimensions, Dimension, Orientation

# use deserialized `dataset`
new_dataset = Transformer.transform_dataset(
    dataset,
    to_pitch_dimensions=PitchDimensions(
        x_dim=Dimension(0, 100),
        y_dim=Dimension(0, 100)
    ),
    to_orientation=Orientation.BALL_OWNING_TEAM
)
```

# Contributing to kloppy
All contributions, bug reports, bug fixes, documentation improvements, enhancements, and ideas are welcome.

A overview on how to contribute can be found in the **[contributing guide](CONTRIBUTING.md)**.

If you are simply looking to start working with the kloppy codebase, navigate to the GitHub "issues" tab and start looking through interesting issues.


