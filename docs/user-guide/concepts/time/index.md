# Time

Soccer data is fundamentally tied to time. Seasons, matches within a season, and events within a match are all ordered. Hence, each event needs to carry information about *when* it happened.

However, the representation of time varies significantly across data providers. Time may be represented using absolute timestamps (e.g., a specific UTC time like *2024-12-01T15:45:13Z*) or through a match-specific game clock (e.g., *75:13*, as seen on a scoreboard). Even when using a game clock, there are further variations, such as how extra time is handled or whether the clock resets at the start of each period.

To address these inconsistencies, kloppy introduces a standardized approach to managing time. In short, the game is split up in periods (i.e., the two 45-minute halves and possibly overtime) which have absolute timestamps to denote their start and end timestamps. Within each period, time is then expressed relatively with respect to the start of the period using a game clock. Let's illustrate this by looking at the time of an event. In kloppy's data model, each record (i.e., event, frame, or code) has a `.time` attribute.

```pycon exec="true" source="console" session="concept-time"
>>> from kloppy import statsbomb

>>> dataset = statsbomb.load_open_data(match_id="3869685")
>>> goal_event = dataset.find("shot.goal")
>>> print(goal_event.time)
```

A [`Time`][kloppy.domain.Time] entity consist of two parts: a reference to a period and a timestamp relative to the kick-off in that period.

```pycon exec="true" source="console" session="concept-time"
>>> print(f"{goal_event.time.period} - {goal_event.time.timestamp}")
```

Let's take a closer look at both of these.

## Periods

[`Period`][kloppy.domain.Period] entities are used to split up a game into periods.

```python exec="true" source="above" session="concept-time"
from kloppy.domain import Period
from datetime import datetime, timezone

periods = [
    Period(
        id=1,
        start_timestamp=datetime(2024, 12, 1, 15, 0, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2024, 12, 1, 15, 45, 10, tzinfo=timezone.utc),
    ),
    Period(
        id=2,
        start_timestamp=datetime(2024, 12, 1, 16, 00, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2024, 12, 1, 16, 48, 30, tzinfo=timezone.utc),
    ),
]
```

Ideally, the [`start_timestamp`][kloppy.domain.Period.start_timestamp] and [`end_timestamp`][kloppy.domain.Period.end_timestamp] values are expressed as absolute time-zone aware `datetime` objects, with the [`start_timestamp`][kloppy.domain.Period.start_timestamp] marking the exact time of the period's kick-off and the [`end_timestamp`][kloppy.domain.Period.end_timestamp] marking the time of the final whistle. This allows users to link and sync different datasets (e.g., tracking data with video).

However, when absolute times are not available, kloppy falls back to using offsets. In this case, the [`start_timestamp`][kloppy.domain.Period.start_timestamp] is defined as the offset between the start of the data feed for the period and the kick-off of the period, while the [`end_timestamp`][kloppy.domain.Period.end_timestamp] is defined as the offset between the start of the data feed and the final whistle of the period. This ensures that even in the absence of absolute time data, a relative timeline is maintained.

```python exec="true" source="above" session="concept-time"
from kloppy.domain import Period
from datetime import timedelta

periods = [
    Period(
        id=1,
        start_timestamp=timedelta(seconds=0),
        end_timestamp=timedelta(minutes=45, seconds=10),
    ),
    Period(
        id=2,
        start_timestamp=timedelta(minutes=60),
        end_timestamp=timedelta(minutes=93, seconds=30),
    ),
]
```

Each period also has an [`id`][kloppy.domain.Period.id]. Therefore, kloppy uses the following convention.

- `1`: First half
- `2`: Second half
- `3`: First half of overtime
- `4`: Second half of overtime
- `5`: Penalty shootout

## Timestamps


The `timestamp` represents the time elapsed since the start of the period. 

```pycon exec="true" source="console" session="concept-time"
>>> rel_time = goal_event.time.timestamp
>>> print(rel_time)
```

The absolute time in the match can be obtained by combining both the `period` and `timestamp`.

```pycon exec="true" source="console" session="concept-time"
>>> abs_time = goal_event.time.period.start_time + goal_event.time.timestamp
>>> print(abs_time)
```

!!! note

    Kloppy uses the built-in `datetime` objects to handle absolute timestamps and `timedelta` objects to handle relative timestamps. Absolute timestamps always include timezone information.


## Operations on time

The [`Time`][kloppy.domain.Time] class supports mathematical operations that allow navigation across different periods and timestamps seamlessly.

### Subtraction (`-`)

You can subtract:

- A `timedelta` from a `Time`, resulting in a new `Time`. If the result would move the `Time` before the start of the current period, it automatically moves back to the previous period if available.
- A `Time` from another `Time`, resulting in a `timedelta`. The periods are taken into account: if they belong to different periods, the full durations of the intermediate periods are summed.

**Examples:**

```python
# Subtracting timedelta
new_time = time_obj - timedelta(seconds=30)

# Subtracting two Time instances
duration = time_obj1 - time_obj2
```

### Addition (`+`)
You can add a `timedelta` to a `Time`, resulting in a new `Time`. If the addition moves the `Time` beyond the end of the current period, it transitions into the next period automatically.

**Examples:**

```python
# Adding timedelta
future_time = time_obj + timedelta(minutes=2)
```
