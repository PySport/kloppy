# Event data

Event (stream) data is **a time-coded feed which describes the key events that occur during a match**. The data is generally [created by trained human annotators](https://fivethirtyeight.com/features/the-people-tracking-every-touch-pass-and-tackle-in-the-world-cup/) (assisted by computer vision) based on broadcast video of a game. Most of the events they annotate are on-the-ball player actions such as shots, passes, and dribbles. However, the data feed will typically also include other relevant events like substitutions and tactical changes. As an example, we load the [open StatsBomb event data](https://github.com/statsbomb/open-data) of the 2002 World Cup final.

```python exec="true" source="above" session="concept-eventdata"
from kloppy import statsbomb

dataset = statsbomb.load_open_data(match_id="3869685")
```

This will create an [`EventDataset`][kloppy.domain.EventDataset] that wraps a list of [`Event`][kloppy.domain.Event] entities and implements a number of common operations to process the dataset. This section explains the [`Event`][kloppy.domain.Event] entities. Later sections of the user guide will explain in-depth how to load and process an event dataset.


## Kloppy's event data model

Event data is sold by specialized data vendors such as StatsBomb, Stats Perform (Opta), and Wyscout. All these data vendors annotate the same games but use their own set of event types, attributes, and data formats. This can make it difficult to write software or perform data analyses that can be applied to multiple event data sources. Therefore, kloppy implements its own [**vendor-independent data model**](../../../reference/event-data/index.md) for describing events.

Below is what the kick-off event looks like in the raw data. StatsBomb uses a JSON object to describe each event. You can get this *raw* representation trough the [`.raw_event`][kloppy.domain.Event.raw_event] attribute.

```python exec="true" result="text" session="concept-eventdata"
print(dataset[4].raw_event)
```

For comparison, below is what the same kick-off looks like in kloppy's data model.

```python exec="true" result="text" session="concept-eventdata"
print(dataset[4])
```

Instead of JSON objects, kloppy uses [`Event`][kloppy.domain.Event] objects to represent events. This provides a number of advantages over storing the raw data in a dictionary or data frame, such as better readability, type-safety, and autocompletion in most IDEs. 

Each event has a number of default attributes, which are summarized in the table below.

| Attribute | Type | Description |
|---|---|---|
| [`dataset`][kloppy.domain.Event.dataset] | [`Dataset`][kloppy.domain.Dataset] | Reference to the dataset that includes this event. |
| [`event_id`][kloppy.domain.Event.event_id] | `str` | Unique event identifier provided by the data provider. Alias for `record_id`. |
| [`event_type`][kloppy.domain.Event.event_type] | [`EventType`][kloppy.domain.EventType] | The specific type of event, such as pass, shot, or foul. |
| [`event_name`][kloppy.domain.Event.event_name] | `str` | Human-readable name of the event type. |
| [`time`][kloppy.domain.Event.time] | [`Time`][kloppy.domain.Time] | Time during the match when the event occurs. |
| [`coordinates`][kloppy.domain.Event.coordinates] | [`Point`][kloppy.domain.Point] | The location on the pitch where the event took place. |
| [`team`][kloppy.domain.Event.team] | [`Team`][kloppy.domain.Team] | The team associated with the event. |
| [`player`][kloppy.domain.Event.player] | [`Player`][kloppy.domain.Player] | The player involved in the event. |
| [`ball_owning_team`][kloppy.domain.Event.ball_owning_team] | [`Team`][kloppy.domain.Team] | The team in possession of the ball at the time of the event. |
| [`ball_state`][kloppy.domain.Event.ball_state] | [`BallState`][kloppy.domain.BallState] | Indicates whether the ball is in play or not. |
| [`raw_event`][kloppy.domain.Event.raw_event] | `object` | The original event data as received from the provider. |
| [`prev_record`][kloppy.domain.Event.prev_record] | [`Event`][kloppy.domain.Event] | Link to the previous event in the sequence. |
| [`next_record`][kloppy.domain.Event.next_record] | [`Event`][kloppy.domain.Event] | Link to the next event in the sequence. |
| [`related_event_ids`][kloppy.domain.Event.related_event_ids] | `[str]` | Identifiers of events related to this one. |
| [`freeze_frame`][kloppy.domain.Event.freeze_frame] | [`Frame`][kloppy.domain.Frame] | Snapshot showing all players’ locations at the time of the event. |
| [`attacking_direction`][kloppy.domain.Event.attacking_direction] | [`AttackingDirection`][kloppy.domain.AttackingDirection] | The direction the team is attacking during this event. |
| [`state`][kloppy.domain.Event.state] | `{str -> object}` | Additional contextual information about the game state. |


### Event types

Each event has a specific type, corresponding to passes, shots, tackles, etc. These event types are implemented as different subclasses of [`Event`][kloppy.domain.Event]. For example, a pass is implemented by the [`PassEvent`][kloppy.domain.PassEvent] subclass, while a substitution is implemented by the [`SubstitutionEvent`][kloppy.domain.SubstitutionEvent] subclass. Each subclass implements additional attributes specific to that event type. For example, a pass has a [`.result`][kloppy.domain.PassEvent] attribute (a pass can be complete, incomplete, out, or offside); while a substitution has a [`.replacement_player`][kloppy.domain.SubstitutionEvent] attribute.

Let's look at the opening goal of the 2002 World Cup final as an example. It is a penalty by Lionel Messi.

```pycon exec="true" source="console" session="concept-eventdata"
>>> goal_event = dataset.get_event_by_id("6d527ebc-a948-4cd8-ac82-daced35bb715")
>>> print(goal_event)
```

In kloppy's data model, the penalty is represented by a [`ShotEvent`][kloppy.domain.ShotEvent]. Each [`ShotEvent`][kloppy.domain.ShotEvent] has a [`.result`][kloppy.domain.ShotEvent] attribute that contains a [`ShotResult`][kloppy.domain.ShotResult]. As the penalty was scored, the result here is `ShotResult.GOAL`.

If a particular event type is not included in kloppy's data model, it will be deserialized as a [`GenericEvent`][kloppy.domain.GenericEvent]. For example, kloppy does not (yet) have a data model for ball receival events.

```pycon exec="true" source="console" session="concept-eventdata"
>>> receival_event = dataset.get_event_by_id("0db72b17-bed3-446f-ae22-468480e33ad6")
>>> print(receival_event)
```

For an overview of all event types and their attributes, see the [Event Type Reference](../../../reference/event-data/event-types/index.md).

!!! note

    Kloppy's data model covers the event types and attributes that are commonly used by multiple data vendors. Some vendors might have certain specific event types or attributes that are not implemented in kloppy's data model, but kloppy's data model can easily be [extended](../../loading-data/index.md#event_factory) to support these if needed.


### Qualifiers

In addition to event type-specific attributes, each event can have one or more qualifiers attached to it. While attributes define core properties of an event such as its outcome, qualifiers provide extra context about how an event happened. They add more descriptive details that help with deeper analysis.

For Messi's penalty that we looked at above, kloppy adds a [`SetPieceQualifier`][kloppy.domain.SetPieceQualifier] and a [`BodyPartQualifier`][kloppy.domain.BodyPartQualifier].

```pycon exec="true" source="console" session="concept-eventdata"
>>> print(goal_event.qualifiers)
```

You can check if an event has a qualifier of a certain type using the `.get_qualifier_value()` method.

```pycon exec="true" source="console" session="concept-eventdata"
>>> from kloppy.domain import SetPieceQualifier
>>> sp_qualifiers = goal_event.get_qualifier_value(SetPieceQualifier)
>>> print(sp_qualifiers)
```

For an overview of all qualifiers, see the [Qualifier Type Reference](../../../reference/event-data/qualifiers/index.md).
