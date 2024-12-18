# Domain Concepts { #kloppy.domain }

The [`kloppy.domain`][kloppy.domain] module defines entities that reflect real-world concepts within the domain of soccer match data. These entities serve as the framework upon which kloppy's logic is structured.

## Dataset

The domain concepts are arranged hierarchically. At the highest level, kloppy defines the concept of a [`Dataset`][kloppy.domain.Dataset]. A dataset describes specific aspects of what happened during a single match as a sequence of [`DataRecord`][kloppy.domain.DataRecord] entities. Kloppy defines three main types of match datasets: [`EventDataset`][kloppy.domain.EventDataset], [`TrackingDataset`][kloppy.domain.TrackingDataset], and [`CodeDataset`][kloppy.domain.CodeDataset]. Additionally, a dataset is linked with a [`Metadata`][kloppy.domain.Metadata] entity, which holds all external information that describes the match.

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

First, we descibe the concepts related to each of these three dataset types. Next, we discuss the structure of the metadata.

### EventDataset

An [`EventDataset`][kloppy.domain.EventDataset] is a sequence of [`Event`][kloppy.domain.Event] entities. Each [`Event`][kloppy.domain.Event] is annotated with an [`EventType`][kloppy.domain.EventType], a [`Time`][kloppy.domain.Time] entity describing when the event happend, a [`Team`][kloppy.domain.Team] and [`Player`][kloppy.domain.Player], a [`Point`][kloppy.domain.Point] on the pitch where the event happend, a [`ResultType`][kloppy.domain.ResultType] describing the outcome of the event, a list of [`Qualifier`][kloppy.domain.Qualifier] entities and optionally a tracking data [`Frame`][kloppy.domain.Frame], the ball owning [`Team`][kloppy.domain.Team], [`AttackingDirection`][kloppy.domain.AttackingDirection] of the team executing the event and the [`BallState`][kloppy.domain.BallState].

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
EventDataset -- Event: {
  source-arrowhead: 1
  target-arrowhead: 1
}

EventType: {
  shape: class
}
Time: {
  shape: class
}
Team: {
  shape: class
}
Player: {
  shape: class
}
Point: {
  shape: class
}
ResultType: {
  shape: class
}
Qualifier: {
  shape: class
}
Frame: {
  shape: class
}

Event -- EventType: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- Time: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- Team: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- Player: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- Point: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- ResultType: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- Qualifier: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Event -- Frame: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}


Period: {
  shape: class
}
Time -- Period: +has {
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
"""


# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

### TrackingDataset

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
TrackingDataset -- Frame: +has {
  source-arrowhead: 1
  target-arrowhead: *
}
Time: {
  shape: class
}
Period: {
  shape: class
}
Time -- Period: +has {
  source-arrowhead: *
  target-arrowhead: 1
}
Frame -- Time: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

Point: {
  shape: class
  link: reference/domain/Point
}
Frame -- Point: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

Player: {
  shape: class
}
Team -- Player: +has {
  source-arrowhead: 1
  target-arrowhead: *
}
Frame -- Player: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Position: {
  shape: class
}
Player -- Position: +has {
  source-arrowhead: 1
  target-arrowhead: *
}

Player -- Point: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

Team: {
  shape: class
}
Ground: {
  shape: class
}
Team -- Ground: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
FormationType: {
  shape: class
}
Team -- FormationType: +has {
  source-arrowhead: *
  target-arrowhead: 1
}

Frame -- Team: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

BallState: {
  shape: class
}
Frame -- BallState: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

AttackingDirection: {
  shape: class
}
Frame -- AttackingDirection: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

### CodeDataset

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
CodeDataset -- Code: +has {
  source-arrowhead: 1
  target-arrowhead: *
}
Code -- Time: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
Code -- Team: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

Time: {
  shape: class
}
Period: {
  shape: class
}
Time -- Period: +has {
  source-arrowhead: *
  target-arrowhead: 1
}
Team: {
  shape: class
}
Ground: {
  shape: class
}
Team -- Ground: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}
FormationType: {
  shape: class
}
Team -- FormationType: +has {
  source-arrowhead: *
  target-arrowhead: 1
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

BallState: {
  shape: class
}
Code -- BallState: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

AttackingDirection: {
  shape: class
}
Code -- AttackingDirection: +has {
  source-arrowhead: 1
  target-arrowhead: 1
}

"""

# We simply run `d2` in a subprocess, passing it our diagram as input and capturing its output to print it.
svg = subprocess.check_output(["d2", "--sketch", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```

## Metadata

Each match dataset is linked with a [`Metadata`][kloppy.domain.Metadata] object, containing all external information describing the match. The metadata contains two [`Team`][kloppy.domain.Team] entities that describe the line-ups of both teams, the [`Period`][kloppy.domain.Period] entities that describe the start and end times of each period of the match, the final [`Score`][kloppy.domain.Score], the [`Provider`][kloppy.domain.Provider] that collected the data, the [`Orientation`][kloppy.domain.Orientation] (i.e., playing direction) of both teams, and the [`CoordinateSystem`][kloppy.domain.CoordinateSystem] in which locations are defined.

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
Period: {
  shape: class
}
Metadata -- Period: +has {
  source-arrowhead: 1
  target-arrowhead: 2
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
Orientation: {
  shape: class
}
Metadata -- Orientation: +has {
  source-arrowhead: 1
  target-arrowhead: 2
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
svg = subprocess.check_output(["d2", "-", "-"], input=diagram, stderr=subprocess.DEVNULL, text=True)
print(svg)
```
