# Tracking Data

A tracking data feed provides X/Y/(Z) coordinate data showing **the position of all players and the ball**. The data is collected using in-stadium optical tracking systems or based on broadcast video. In-stadium tracking data typically has a higher accuracy and provides the locations of all players and the ball, while broadcast-based tracking data only includes the positions of on-camera players.

One widely used open dataset is the [Metrica Sports dataset](https://github.com/metrica-sports/sample-data). Below, we demonstrate how to load tracking data from Metrica Sports using kloppy:

```python exec="true" source="above" session="concept-trackingdata"
from kloppy import metrica

dataset = metrica.load_open_data(
    match_id=1, 
    limit=1000  # Optional: load the first 1000 frames only
)
```

This will create a [`TrackingDataset`][kloppy.domain.TrackingDataset] that wraps a list of [`Frame`][kloppy.domain.Frame] entities. The tracking data is sampled at a fixed frame rate, available via the `metadata.frame_rate` attribute.

```pycon exec="true" source="console" session="concept-trackingdata"
>>> print(dataset.metadata.frame_rate)
```

This value represents the number of frames recorded per second. For example, a frame rate of `25` means there are 25 frames per second of game time.

The remainder of this section explains the [`Frame`][kloppy.domain.Frame] entities. Later sections of the user guide will explain in-depth how to process a tracking dataset.

## Kloppy’s tracking data model

Kloppy uses [`Frame`][kloppy.domain.Frame] objects to store tracking data. Each frame contains:

- The exact moment the frame was recorded.
- The (x, y) coordinates of the ball.
- A mapping of player identifiers to their (x, y) coordinates.

To inspect a specific frame, use indexing on the `dataset.frames` list. For example, to access the frame at index 500:

```python exec="true" source="above" session="concept-trackingdata"
frame = dataset.frames[500]
```

### Timestamp

The [`.timestamp`][kloppy.domain.Frame.timestamp] attribute returns a [`Time`][kloppy.domain.Time] object representing when the frame was recorded.

```pycon exec="true" source="console" session="concept-trackingdata"
>>> print(frame.time)
```

For more on the [`Time`][kloppy.domain.Time] object, see the [next section](../time/index.md).


### Ball coordinates

The [`.ball_coordinates`][kloppy.domain.Frame.ball_coordinates] attribute provides the position of the ball as a [`Point`][kloppy.domain.Point] object:

```pycon exec="true" source="console" session="concept-trackingdata"
>>> print(frame.ball_coordinates)
```

Some tracking data providers also include the ball's height (z-axis). In those cases, `.ball_coordinates` will return a [`Point3D`][kloppy.domain.Point3D] object instead.


### Player coordinates

Each [`Frame`][kloppy.domain.Frame] includes a [`.players_coordinates`][kloppy.domain.Frame.players_coordinates] dictionary. This maps each [`Player`][kloppy.domain.Player] object to a [`Point`][kloppy.domain.Point] indicating the player’s location on the pitch.


```pycon exec="true" source="console" session="concept-trackingdata"
>>> print(f"Number of players in the frame: {len(frame.players_coordinates)}")
```

**Example: Coordinates of Home Team Players**

```pycon exec="true" source="console" session="concept-trackingdata"
>>> home_team, away_team = dataset.metadata.teams
>>> print("List home team players coordinates", [
...    player_coordinates 
...    for player, player_coordinates
...    in frame.players_coordinates.items()
...    if player.team == home_team
... ])
```
