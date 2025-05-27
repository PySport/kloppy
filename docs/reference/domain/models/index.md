[](){ #kloppy.domain }
# Domain Concepts

The `kloppy.domain` module defines entities that reflect real-world concepts within the domain of soccer match data. These entities serve as the framework upon which kloppy's logic is structured. The domain concepts are arranged hierarchically. At the highest level, kloppy defines the concept of a [Dataset](#dataset). Each dataset is linked with a [Metadata](#metadata) entity, which holds all external information that describes the dataset.

## Dataset

A [`Dataset`][kloppy.domain.Dataset] describes specific aspects of what happened during a single match as a sequence of [`DataRecord`][kloppy.domain.DataRecord] entities. Kloppy defines three main types of match datasets: [EventDataset](#eventdataset), [TrackingDataset](#trackingdataset), and [CodeDataset](#codedataset).

```python exec="true" html="true"
import subprocess

diagram = """
Dataset: {
  shape: parallelogram
}
EventDataset: {
  shape: class
}
Dataset -> EventDataset: {
  target-arrowhead.shape: triangle
  target-arrowhead.style.filled: false
}
TrackingDataset: {
  shape: class
}
Dataset -> TrackingDataset: {
  target-arrowhead.shape: triangle
  target-arrowhead.style.filled: false
}
CodeDataset: {
  shape: class
}
Dataset -> CodeDataset: {
  target-arrowhead.shape: triangle
  target-arrowhead.style.filled: false
}

DataRecord: {
  shape: parallelogram
}
Dataset -- DataRecord: +consists of {
  source-arrowhead: 1
  target-arrowhead: *
}

Event: {
  shape: class
}
DataRecord -> Event: {
  target-arrowhead.shape: triangle
  target-arrowhead.style.filled: false
}
Frame: {
  shape: class
}
DataRecord -> Frame: {
  target-arrowhead.shape: triangle
  target-arrowhead.style.filled: false
}
Code: {
  shape: class
}
DataRecord -> Code: {
  target-arrowhead.shape: triangle
  target-arrowhead.style.filled: false
}

Metadata: {
  shape: rectangle
}
Dataset -- Metadata: +has {
  source-arrowhead: *
  target-arrowhead: 1
}
"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

First, we describe the entities related to each of these three dataset types. Next, we discuss the structure of the metadata.

### EventDataset

An [`EventDataset`][kloppy.domain.EventDataset] is a chronologically ordered sequence of [`Event`][kloppy.domain.Event] entities. Each [`Event`][kloppy.domain.Event] represents an on-the-ball action (e.g., pass, shot, tackle) or tactical change (e.g., substitution) and is annotated with a set of attributes that describe the event:

- an [`EventType`][kloppy.domain.EventType],
- a [`Time`][kloppy.domain.Time] when the event happened,
- a [`Team`][kloppy.domain.Team] involved in the event,
- the [`AttackingDirection`][kloppy.domain.AttackingDirection] of the team executing the event,
- the ball owning [`Team`][kloppy.domain.Team],
- a [`Player`][kloppy.domain.Player] involved in the event,
- a [`Point`][kloppy.domain.Point] on the pitch where the event happened,
- the [`BallState`][kloppy.domain.BallState] during the event,
- a list of [`Qualifier`][kloppy.domain.Qualifier] entities providing additional details, and
- optionally a tracking data [`Frame`][kloppy.domain.Frame].

Depending on the [`EventType`][kloppy.domain.EventType], an event can have additional attributes.

```python exec="true" html="true"
import subprocess

diagram = """
EventDataset: {
  shape: class
}
Event: {
  shape: class

  +event_id: str
  +event_type: EventType
  +event_name: str
  +time: Time
  +team: Team
  +player: Player
  +coordinates: Point
  +result: ResultType
  +raw_event: obj
  +state: dict
  +related_event_ids: "[]str"
  +qualifiers: "[]Qualifier"
  +freeze_frame: "Frame"

  +attacking_direction: AttackingDirection
  +ball_owning_team: Team
  +ball_state: BallState
}
direction: right
EventDataset -- Event: {
  source-arrowhead: 1
  target-arrowhead: 1
}
"""


# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

### TrackingDataset

A [`TrackingDataset`][kloppy.domain.TrackingDataset] is a sequence of [`Frame`][kloppy.domain.Frame] entities. Each frame describes the locations of the ball and the players as a [`Point`][kloppy.domain.Point] on the pitch at a particular [`Time`][kloppy.domain.Time].

```python exec="true" html="true"
import subprocess

diagram = """
TrackingDataset: {
  shape: class
}
Frame: {
  shape: class

  +frame_id: str
  +time: Time
  +ball_coordinates: Point3D
  +players_data: "Player -> PlayerData"
  +ball_speed: float
  +other_data: dict

  +attacking_direction: AttackingDirection
  +ball_owning_team: Team
  +ball_state: BallState
}
direction: right
TrackingDataset -- Frame: +has {
  source-arrowhead: 1
  target-arrowhead: *
}
"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

### CodeDataset


A [`CodeDataset`][kloppy.domain.CodeDataset] is a sequence of [`Code`][kloppy.domain.Code] entities, each representing a tagged event within a match.

```python exec="true" html="true"
import subprocess

diagram = """
CodeDataset: {
  shape: class
}
Code: {
  shape: class

  +code_id: str
  +code: str
  +time: Time
  +end_timestamp: timedelta
  +labels: "str -> bool | str"

  +attacking_direction: AttackingDirection
  +ball_owning_team: Team
  +ball_state: BallState
}
direction: right
CodeDataset -- Code: +has {
  source-arrowhead: 1
  target-arrowhead: *
}
"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

## Metadata

A [`Metadata`][kloppy.domain.Metadata] object contains all external information describing the match: two [`Team`][kloppy.domain.Team] entities that describe the line-ups of both teams, the [`Period`][kloppy.domain.Period] entities that describe the start and end times of each period of the match, the final [`Score`][kloppy.domain.Score], the [`Provider`][kloppy.domain.Provider] that collected the data, the [`Orientation`][kloppy.domain.Orientation] (i.e., playing direction) of both teams, and the [`CoordinateSystem`][kloppy.domain.CoordinateSystem] in which locations are defined.

```python exec="true" html="true"
import subprocess

diagram = """
Metadata: {
  shape: class
}
Dataset -- Metadata: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

Team: {
  shape: class
}
Metadata -- Team: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
Ground: {
  shape: class
}
Team -- Ground: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
FormationType: {
  shape: class
}
Team -- FormationType: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
Player: {
  shape: class
}
Team -- Player: +has {
  source-arrowhead: 1
  target-arrowhead: *
}
Position: {
  shape: class
}
Player -- Position: +has {
  source-arrowhead: 1
  target-arrowhead: *
}

Period: {
  shape: class
}
Metadata -- Period: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}


Orientation: {
  shape: class
}
Metadata -- Orientation: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}

CoordinateSystem: {
  shape: class
}
Metadata -- CoordinateSystem: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
Origin: {
  shape: class
}
CoordinateSystem -- Origin: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
VerticalOrientation: {
  shape: class
}
CoordinateSystem -- VerticalOrientation: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
PitchDimensions: {
  shape: class
}
CoordinateSystem -- PitchDimensions: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Provider: {
  shape: class
}
Metadata -- Provider: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
Score: {
  shape: class
}
Metadata -- Score: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
DatasetFlag: {
  shape: class
}
Metadata -- DatasetFlag: +has {
  source-arrowhead: 1
  target-arrowhead: 2
}
"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```
