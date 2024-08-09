# Event data

An event data feed is a time-coded feed that lists high-level semantic events and player actions in a match. Each record in the feed includes a team, event, type, and timestamp for each action. Furthermore, every event has a series of attributes and qualifiers describing it that depend on the event’s type. You will find explanations of every possible event type, its attributes and qualifiers that are supported in kloppy in our complete lists of Events Types and Qualifier Types.

You can load an example event data set as follows:

```python
from kloppy import statsbomb

dataset = statsbomb.load_open_data()
```

An event data feed is deserialized into an EventDataset that groups all events of a single game and provides you with utility functions to navigate and visualize the dataset. Examples illustrating how to load data from other sources can be found in … The following tutorials explain how to analyse the data:

Loading event stream data
Navigating event stream data
Visualizing event stream data
Attribute transformers
Defining custom Event classes
Synchronizing event data with tracking data
Transforming to a Pandas or Polars dataframe format

In the reminder of this section we describe the standardized data model that kloppy uses for representing event data.
