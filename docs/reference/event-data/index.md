# Event Data Model

This section outlines the current state of kloppy's event data model. Each [`Event`][kloppy.domain.Event] consists of general attributes as well as event-specific attributes. The general attributes listed below are recorded for all event types, based on their applicability. Additional attributes are recorded depending on the specific [`EventType`][kloppy.domain.EventType].

Attribute|Type|Description
---|---|---
`event_id`|_str_|Unique identifier for each event given by provider.
`event_type`|[`EventType`][kloppy.domain.EventType]|The type of event.
`event_name`|_str_|Textual representation of the event type.
`time`|[`Time`][kloppy.domain.Time]|Time in the match the event takes place.
`coordinates`|[`Point`][kloppy.domain.Point]|Coordinates where event happened.
`result`|[`ResultType`][kloppy.domain.ResultType]|The outcome of the event.
`team`|[`Team`][kloppy.domain.Team]|The team this event relates to.
`player`|[`Player`][kloppy.domain.Player]|The player this event relates to.
`ball_owning_team`|[`Team`][kloppy.domain.Team]|Team in control of the ball during the event.
`ball_state`|[`BallState`][kloppy.domain.BallState]|Whether the ball is in play.
`qualifiers`|_List[[`Qualifier`][kloppy.domain.Qualifier]]_|A list of qualifiers providing additional information about the event.
`raw_event`|_object_|The provider's original representation of the event.
`dataset`|[`Dataset`][kloppy.domain.Dataset]|A reference to the dataset the event is part of.
`prev_record`|[`Event`][kloppy.domain.Event]|A reference to the previous event.
`next_record`|[`Event`][kloppy.domain.Event]|A reference to the next event.
`related_event_ids`|_List[str]_|List of related event ids.
`freeze_frame`|[`Frame`][kloppy.domain.Frame]|A tracking data frame related to the event.
`attacking_direction`|[`AttackingDirection`][kloppy.domain.AttackingDirection]|The playing direction of the home team during the event.

!!! warning

    The implementation of the data model is not yet complete for all providers and some providers might simply
    not support certain parts of the data model (e.g., not all providers annotate the intended recipient of
    a pass). For each event type and qualifier, we provide a detailed overview describing if and how it is
    implemented for each data provider.

    The status of the implementation is indicated by the following icons:

      - :material-check: the implementation is complete
      - :material-close: not supported by the data provider
      - :material-progress-helper: not yet implemented
      - :material-progress-question: the status is unclear
