# Tracking data

A tracking data feed provides X/Y/Z coordinate data showing the position of all players and the ball, typically sampled at a rate of 20 or 25 frames per second.

You can load an example event data set as follows:

```python
from kloppy import metrica

dataset = metrica.load_open_data(limit=10)
```

In the remainder of this section we describe the standardised data model that kloppy uses for representing event data.
