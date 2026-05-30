# Enriching Event Data with Tracking Data

This guide demonstrates how to enrich an `EventDataset` with `PressureEvent`s derived from a `TrackingDataset`. We will use Sportec data from the IDSSE dataset to identify sequences of frames where a player is within a radius $r$ of the player in possession, create `PressureEvent`s for these sequences, and insert them into the `EventDataset`.

## Loading Data

First, we load both the event and tracking data for a specific match from the IDSSE dataset. When working with both datasets together, it is important to transform them to a common orientation and coordinate system to ensure the coordinates are comparable. We will use the `HOME_AWAY` orientation, where the home team plays from left to right in the first half.

```python exec="true" source="above" session="enrich-tracking"
from kloppy import sportec
from kloppy.domain import Orientation

match_id = "J03WPY" # Fortuna Düsseldorf vs. 1. FC Nürnberg

# Load event data and transform to HOME_AWAY orientation
event_dataset = sportec.load_open_event_data(match_id=match_id)
event_dataset = event_dataset.transform(
    to_orientation=Orientation.HOME_AWAY
)

# Load tracking data and transform to the same orientation
tracking_dataset = sportec.load_open_tracking_data(match_id=match_id, sample_rate=1/10)
tracking_dataset = tracking_dataset.transform(
    to_orientation=Orientation.HOME_AWAY
)

print(f"Loaded {len(event_dataset)} events and {len(tracking_dataset)} tracking frames.")
```

## Identifying Pressure Sequences

We define "pressure" as an opponent being within 3 meters of the player in possession. To find the player in possession in each frame, we look for the player from the ball-owning team who is closest to the ball. We use the `distance_between` method from the `PitchDimensions` class to calculate distances in meters.

```python exec="true" source="above" session="enrich-tracking"
from kloppy.domain import BallState

pitch_dimensions = tracking_dataset.metadata.pitch_dimensions

RADIUS = 3.0  # meters
BALL_DIST_THRESHOLD = 1.0 # meters to consider a player has possession

pressure_sequences = [] # List of (player, start_frame, end_frame)
active_pressures = {}   # Mapping player -> start_frame

for frame in tracking_dataset:
    # Skip frames where the ball is dead or coordinates are missing
    if not frame.ball_coordinates or frame.ball_state != BallState.ALIVE:
        # Close all active pressures when the ball is dead
        for player, start_frame in active_pressures.items():
            pressure_sequences.append((player, start_frame, frame))
        active_pressures = {}
        continue
        
    # Find player in possession (closest to ball from the owning team)
    possessor = None
    min_ball_dist = float('inf')
    for player, player_data in frame.players_data.items():
        if player.team != frame.ball_owning_team:
            continue
        dist = pitch_dimensions.distance_between(player_data.coordinates, frame.ball_coordinates)
        if dist < min_ball_dist:
            min_ball_dist = dist
            possessor = player
            
    if not possessor or min_ball_dist > BALL_DIST_THRESHOLD:
        # No clear possession, close all active pressures
        for player, start_frame in active_pressures.items():
            pressure_sequences.append((player, start_frame, frame))
        active_pressures = {}
        continue

    # Find opponents within RADIUS of the possessor
    possessor_coords = frame.players_data[possessor].coordinates
    for player, player_data in frame.players_data.items():
        if player.team == possessor.team:
            continue
            
        dist = pitch_dimensions.distance_between(player_data.coordinates, possessor_coords)
        if dist < RADIUS:
            if player not in active_pressures:
                active_pressures[player] = frame
        else:
            if player in active_pressures:
                pressure_sequences.append((player, active_pressures.pop(player), frame))

# Close any remaining active pressures at the end of the dataset
for player, start_frame in active_pressures.items():
    pressure_sequences.append((player, start_frame, tracking_dataset[-1]))

print(f"Identified {len(pressure_sequences)} potential pressure sequences.")
```

## Creating and Inserting PressureEvents

Now we create `PressureEvent` objects from the identified sequences and insert them into our `event_dataset`. We use the `EventFactory` to simplify event creation and the `insert` method to ensure they are placed in the correct chronological order.

```python exec="true" source="above" session="enrich-tracking"
from kloppy.domain import EventFactory, PressureEvent

factory = EventFactory()

inserted_count = 0
for player, start_frame, end_frame in pressure_sequences:
    # Only consider sequences that lasted at least 0.5 seconds to filter out noise
    duration = (end_frame.timestamp - start_frame.timestamp).total_seconds()
    if duration < 0.5:
        continue
        
    pressure_event = factory.build_pressure_event(
        event_id=f"pressure-{player.player_id}-{start_frame.frame_id}",
        period=start_frame.period,
        timestamp=start_frame.timestamp,
        end_timestamp=end_frame.time, # PressureEvent requires end_timestamp as a Time object
        team=player.team,
        player=player,
        coordinates=start_frame.players_data[player].coordinates,
        ball_owning_team=start_frame.ball_owning_team,
        ball_state=start_frame.ball_state,
        result=None,
        qualifiers=[],
        raw_event=None
    )
    
    # Insert the event into the dataset based on its timestamp
    event_dataset.insert(pressure_event, timestamp=pressure_event.timestamp)
    inserted_count += 1

print(f"Inserted {inserted_count} PressureEvents into the EventDataset.")
```

## Contextualizing Events: Pressured vs. Unpressured Passes

We can now use these `PressureEvent`s to contextualize existing events. For example, we can flag every `PassEvent` that occurred while an opponent was applying pressure to the passer. Instead of searching the entire dataset for each pass, we can efficiently use the `prev` and `next` records.

```python exec="true" source="above" session="enrich-tracking"
from kloppy.domain import UnderPressureQualifier, PassEvent, PassResult
from datetime import timedelta

# Flag passes as being under pressure
for event in event_dataset:
    if not isinstance(event, PassEvent):
        continue
        
    is_pressured = False
    
    # Check predecessors: since PressureEvents are inserted by start time, 
    # the containing pressure must be at or before this event in the sequence.
    other = event.prev(lambda x: isinstance(x, PressureEvent))
    while other and event.time - other.time < timedelta(seconds=20):
        if other.team != event.team and other.time <= event.time <= other.end_timestamp:
            is_pressured = True
            break
        other = other.prev(lambda x: isinstance(x, PressureEvent))
        
    # Check successors: only needed if they have the exact same timestamp
    if not is_pressured:
        other = event.next(lambda x: isinstance(x, PressureEvent))
        while other and other.time == event.time:
            if other.team != event.team and other.time <= event.time <= other.end_timestamp:
                is_pressured = True
                break
            other = other.next(lambda x: isinstance(x, PressureEvent))
    
    if is_pressured:
        event.qualifiers.append(UnderPressureQualifier(value=True))

# Analysis: Completion Rate
pressured_passes = [e for e in event_dataset if isinstance(e, PassEvent) and e.get_qualifier_value(UnderPressureQualifier)]
unpressured_passes = [e for e in event_dataset if isinstance(e, PassEvent) and not e.get_qualifier_value(UnderPressureQualifier)]

def get_completion_rate(passes):
    if not passes:
        return 0
    complete = sum(1 for p in passes if p.result == PassResult.COMPLETE)
    return (complete / len(passes)) * 100

print(f"Pressured Pass Completion: {get_completion_rate(pressured_passes):.1f}% ({len(pressured_passes)} passes)")
print(f"Unpressured Pass Completion: {get_completion_rate(unpressured_passes):.1f}% ({len(unpressured_passes)} passes)")
```

## Analysis: Who Pressed Most?

Finally, we can analyze the enriched dataset to find out which player performed the most pressure actions.

```python exec="true" source="above" session="enrich-tracking"
from collections import Counter

pressure_counts = Counter(
    event.player.full_name 
    for event in event_dataset 
    if isinstance(event, PressureEvent)
)

print("Top 10 players by number of pressure actions:")
for name, count in pressure_counts.most_common(10):
    print(f"{name}: {count}")
```
