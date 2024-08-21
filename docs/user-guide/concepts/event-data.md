# Event data

An event data feed is a time-coded feed that lists high-level semantic events and player actions in a match. Each record in the feed includes a team, event, type, and timestamp for each action. Furthermore, every event has a series of attributes and qualifiers describing it that depend on the event’s type. You will find explanations of every possible event type, its attributes and qualifiers that are supported in kloppy in our complete lists of Events Types and Qualifier Types.

You can load an example event data set as follows:

```python
from kloppy import statsbomb

dataset = statsbomb.load_open_data()
```

In the reminder of this section we describe the standardized data model that kloppy uses for representing event data.
