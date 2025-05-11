# Exporting to a dataframe

Kloppy datasets can be easily exported to either [Pandas](https://pandas.pydata.org/) or [Polars](https://pola.rs/) dataframes. This functionality connects kloppy with the broader Python data analytics ecosystem, enabling you to:

- Explore and manipulate tracking or event data using Pandas or Polars.
- Export data to formats like CSV, Excel, or Parquet.
- Perform advanced feature engineering on-the-fly.
- Integrate with machine learning and visualization libraries that require tabular input.

```python exec="true" session="export-df"
# Load some data for the examples below. Not displayed
from kloppy import sportec
event_dataset = sportec.load_open_event_data(match_id="J03WN1")

tracking_dataset = sportec.load_open_tracking_data(match_id="J03WN1", limit=10)

from datetime import timedelta

from kloppy.domain import Code, CodeDataset, EventType

code_dataset = (
    CodeDataset
    .from_dataset(
        event_dataset.filter("shot"),
        lambda event: Code(
            code_id=None,  # make it auto increment on write
            code=event.event_name,
            period=event.period,
            timestamp=max(timedelta(seconds=0), event.timestamp - timedelta(seconds=7)),  # start 7s before the shot
            end_timestamp=event.timestamp + timedelta(seconds=5),  # end 5s after the shot
            labels={
                'Player': str(event.player),
                'Team': str(event.team)
            },

            # in the future, the next two won't be needed anymore
            ball_owning_team=None,
            ball_state=None,
            statistics=None
        )
    )
)
```


## Basic usage
Kloppy represents data using structured Python objects (like [`TrackingDataset`][kloppy.domain.TrackingDataset] and [`EventDataset`][kloppy.domain.EventDataset]). The [`to_df()`][kloppy.domain.Dataset.to_df] method flattens these objects into a tabular form.

```python
df = dataset.to_df()
```

The default output columns of the DataFrame depend on the type of dataset:

### Event data

For an [`EventDataset`][kloppy.domain.EventDataset], the default columns include:

| Column           | Description                                 |
|------------------|---------------------------------------------|
| event_id         | Unique identifier of the event              |
| event_type       | Type of the event (e.g., pass, shot)         |
| period_id        | Match period                                |
| timestamp        | Start time of the event                     |
| end_timestamp    | End time of the event (if available)         |
| team_id          | ID of the team performing the event         |
| player_id        | ID of the player performing the event       |
| result           | Result of the action (e.g., COMPLETE)       |
| success          | Boolean indicating if the event was completed successfully |
| coordinates_x/y  | Location of the event on the pitch          |
| ball_state       | Current state of the game                   |
| ball_owning_team | Which team owns the ball                    |

Other columns are added depending on the event types and qualifiers of the events in the dataset.

**Example:**

```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{event_dataset.to_df().head(n=3).to_html(index=False, border="0")}
</div></div>
""")
```


### Tracking data

For a [`TrackingDataset`][kloppy.domain.TrackingDataset], the output columns include:

| Column                                          | Description                           |
|-------------------------------------------------|---------------------------------------|
| frame_id                                        | Frame number                          |
| period_id                                       | Match period                          |
| timestamp                                       | Frame timestamp                       |
| ball_x, ball_y, ball_z, ball_speed               | Ball position and speed               |
| <player_id\>_x, <player_id\>_y, <player_id\>_d, <player_id\>_s | Player coordinates, distance (since previous frame), and speed |
| ball_state       | Current state of the ball                   |
| ball_owning_team | Which team owns the ball                    |

**Example:**

```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{tracking_dataset.to_df().head(n=3).to_html(index=False, border="0")}
</div></div>
""")
```


### Code data

For a [`CodeDataset`][kloppy.domain.CodeDataset], the output columns include:


| Column                                          | Description                           |
|-------------------------------------------------|---------------------------------------|
| code_id                                         | Code number                           |
| period_id                                       | Match period                          |
| timestamp                                       | Start timestamp                       |
| end_timestamp                                   | End timestamp                         |
| code                                            | Name of the code                      |

Furthermore, one column is added for each label used in the dataset.

**Example:**

```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{code_dataset.to_df().head(n=3).to_html(index=False, border="0")}
</div></div>
""")
```


## Selecting output columns
You can control which attributes are included in the output using arguments in `.to_df()`.
Wildcard patterns (`*`) are supported to match multiple fields:

```python exec="true" source="above" session="export-df"
df = event_dataset.to_df("event_type", "team", "coordinates_*")
```


```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{df.head(n=1).to_html(index=False, border="0")}
</div></div>
""")
```

This lets you include only the data you need, making downstream processing more efficient. The pattern is matched against all default attributes provided by the internal transformer.

## Adding metadata as columns
You can inject constant metadata into your DataFrame by passing keyword arguments:

```python exec="true" source="above" session="export-df"
df = event_dataset.to_df("*", match_id="match_1234", competition="Premier League")
```


```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{df.head(n=1).to_html(index=False, border="0")}
</div></div>
""")
```

These keyword arguments will be added as constant columns across all rows. This is useful for adding identifiers or context to the exported data.

## Attribute transformers
Attribute Transformers let you derive new attributes on the fly during the conversion process. Kloppy includes a limited set of built-in transformers:

- `DistanceToGoalTransformer`: Compute the distance to the goal.
- `DistanceToOwnGoalTransformer`: Compute the distance to the own goal.
- `AngleToGoalTransformer`: Compute the angle between the current location and the center of the goal.

**Example usage:**

```python exec="true" source="above" session="export-df"
from kloppy.domain.services.transformers.attribute import DistanceToGoalTransformer
from kloppy.domain import Orientation

df = (
    event_dataset
    .to_df("event_type", "team", "coordinates_*", DistanceToGoalTransformer())
)
```

```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{df.head(n=1).to_html(index=False, border="0")}
</div></div>
""")
```


You can also define your own custom transformer. A transformer is a function that takes an Event (or Frame) and returns a dictionary of derived values:

```python exec="true" source="above" session="export-df"
def my_transformer(event):
    return {
        "is_shot": event.event_type.name == "SHOT",
        "x": event.coordinates.x if event.coordinates else None
    }

df = event_dataset.to_df("event_type", "team", "coordinates_*", my_transformer)
```

```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{df.head(n=1).to_html(index=False, border="0")}
</div></div>
""")
```

Alternatively, you can add named attributes using keyword arguments and pass a callable that returns any single value:

```python exec="true" source="above" session="export-df"
df = event_dataset.to_df(
    "event_type", "team", "coordinates_*", 
    is_pass=lambda event: event.event_type.name == "PASS"
)
```

```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{df.head(n=1).to_html(index=False, border="0")}
</div></div>
""")
```

This flexibility allows you to calculate exactly the attributes you need at export time.


## Combine it all
Here's an example that shows everything working together:

```python exec="true" source="above" session="export-df"
from kloppy import sportec
from kloppy.domain.services.transformers.attribute import DistanceToGoalTransformer

event_dataset = sportec.load_open_event_data(match_id="J03WN1")

df = event_dataset.to_df(
    "event_type", "team", "coordinates_*",
    DistanceToGoalTransformer(),
    match_id="match_5678",
    is_pass=lambda e: e.event_type.name == "PASS"
)
```


```python exec="true" html="true" session="export-df"
print(f"""
<div class="md-typeset__scrollwrap"><div class="md-typeset__table">
{df.head(n=3).to_html(index=False, border="0")}
</div></div>
""")
```


