# Tracking data

A tracking data feed provides X/Y/Z coordinate data showing the position of all players and the ball, typically sampled at a rate of 20 or 25 frames per second.

You can load an example event data set as follows:

```python
from kloppy import metrica

dataset = metrica.load_open_data(limit=10)
```

This gives you a TrackingDataset that groups all events of a simple game and provides you with utility functions to navigate the dataset. Examples illustrating how to load data from other sources can be found in … The following tutorials explain how to analyse the data:

Loading tracking data
Transforming to a Pandas or Polars dataframe format

In the remainder of this section we describe the standardised data model that kloppy uses for representing event data.
