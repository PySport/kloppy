# Inserting events

Sometimes event data is incomplete, and you need to manually
inject events into a dataset. The [`.insert()`][kloppy.domain.EventDataset.insert]
method allows you to add [`Event`][kloppy.domain.Event] objects to an existing
[`EventDataset`][kloppy.domain.EventDataset].

Common use cases include:

- Deduce and insert synthetic events that providers don't annotate (e.g., generating "Carry" events).
- Insert events that are provided in metadata rather than the event stream (e.g., substitutions with approximate timestamps).
- Insert events derived from a tracking dataset (e.g., adding "Pressing" events).

The method automatically handles the re-linking of the dataset (updating
`prev_record` and `next_record` references) to ensure the integrity of the
event stream.

## Basic setup

To insert an event, you first need to create the
[`Event`][kloppy.domain.Event] object. You can use
the [`EventFactory`][kloppy.domain.EventFactory] to build specific event types.

```python
from datetime import timedelta
from kloppy.domain import EventFactory, CarryResult

# Create a new event
new_event = EventFactory().build_carry(
    event_id="added-carry-1",
    timestamp=timedelta(seconds=700),
    result=CarryResult.COMPLETE,
    period=dataset.metadata.periods[0],
    ball_owning_team=dataset.metadata.teams[0],
    team=dataset.metadata.teams[0],
    player=dataset.metadata.teams[0].players[0],
    coordinates=(0.2, 0.3),
    end_coordinates=(0.22, 0.33)
)
```

## Insertion methods

There are four ways to determine where the new event is placed in the dataset.

### By position (index)

If you know the exact index where the event should be located, you can use the
`position` argument. This works exactly like a standard Python list insertion.

```python
# Insert the event at index 3
dataset.insert(new_event, position=3)
```

### By event ID

If you do not know the index but know the context (e.g., the event should
happen immediately before or after a specific action), you can use the
`before_event_id` or `after_event_id` arguments.

```python
# Insert immediately before a specific event
dataset.insert(new_event, before_event_id="event-id-100")

# Insert immediately after a specific event
dataset.insert(new_event, after_event_id="event-id-305")
```

### By timestamp

To insert the event chronologically, provide the `timestamp` argument. The
dataset will be searched to find the correct location based on the time
provided.

```python
# Insert based on the timestamp defined in the new_event
dataset.insert(new_event, timestamp=new_event.timestamp)
```

### Using a scoring function

For complex insertion logic—such as ''insert after the closest event belonging
to Team A''—you can provide a `scoring_function`.

The function iterates over events in the dataset. It must accept an `event`
and the `dataset` as arguments and return a number:

- **Positive Score:** Insert **after** the event with the highest score.
- **Negative Score:** Insert **before** the event with the highest absolute score.
- **Zero:** No match.

**Example: Insert after the closest timestamp**

```python
def insert_after_closest_match(event, dataset):
    # Filter logic: only check events for the same team and period
    if event.ball_owning_team != dataset.metadata.teams[0]:
        return 0
    if event.period != new_event.period:
        return 0
        
    # Scoring logic: The smaller the time difference, the higher the score
    time_diff = abs(event.timestamp.total_seconds() - new_event.timestamp.total_seconds())
    return 1 / time_diff if time_diff != 0 else 0

dataset.insert(new_event, scoring_function=insert_after_closest_match)
```
