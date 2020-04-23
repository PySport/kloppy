# kloppy: standardizing soccer tracking- and event data
--------
## What is it?

**kloppy** is a Python package providing deserializers for soccer tracking- and event data, and
standardized data models designed to make working with different tracking- and event data like
a breeze. It aims to be the fundamental building blocks for loading tracking- and event data.

## Main Features
Here are just a few of the things that kloppy does well:
- Out-of-the-box [**Deserializing**][deserializing] tracking- and event data from different source into a standardized model
- Flexible [**coordinate system**][coordinate-system] transformation for mapping from one source to another source (eg OPTA -> TRACAB)
- Intelligent [**orientation][orientation] changing helpers (eg from TRACAB fixed orientation to "Home Team" orientation)

## Where to get it
The source code is currently hosted on GitHub at:
https://github.com/PySport/kloppy

Installers for the latest released version are available at the [Python
package index](https://pypi.org/project/kloppy).

```sh
# or PyPI
pip install kloppy
```


### Deserializing data
When working with tracking- or event data we need to deserialize it from the format the provider uses.
The kloppy package provides TRACAB (from ChyronHego) deserializer from now.
```python
from kloppy import TRACABSerializer

serializer = TRACABSerializer()

with open("tracab_data.dat", "rb") as data, \
        open("tracab_metadata.xml", "rb") as meta:

    data_set = serializer.deserialize(
        data=data,
        metadata=meta,
        options={
            "sample_rate": 1 / 12
        }
    )
    
    # start working with data_set
```


```python
from kloppy.domain import Transformer, CoordinateSystem, Scale, Orientation, BallOwningTeam

# use deserialized `data_set`
new_data_set = Transformer.transform_data_set(
    data_set,
    to_coordinate_system=CoordinateSystem(
        x_scale=Scale(0, 100),
        y_scale=Scale(0, 100)
    ),
    to_orientation=Orientation.BALL_OWNING_TEAM
)
```



### TODO List
Tracking data deserializers
- [x] TRACAB
- [ ] MetricaSports
- [ ] BallJames

Event data deserializers
- [ ] OPTA
- [ ] StatsBomb
- [ ] MetricaSports

Exporter
- [ ] Pandas dataframe