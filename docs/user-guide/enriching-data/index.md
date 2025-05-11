# Enriching Event Data with State Information

While working with event data, it can be helpful to include contextual game state information such as the current score, the players on the pitch, or the team formation. In kloppy, you can use the [`.add_state()`][kloppy.domain.EventDataset.add_state] method to enrich event data with different types of state: `score`, `lineup`, and `formation`.

## Loading Event Data

We'll start by loading the StatsBomb open dataset of the match between Barcelona and Deportivo Alavés.

```python
from kloppy import statsbomb
from kloppy.domain import EventType

dataset = statsbomb.load_open_data()
print([team.name for team in dataset.metadata.teams])
print(dataset.events[0].state)
```

You should see:

```
['Barcelona', 'Deportivo Alavés']
{}
```

At this point, the events don't yet contain any state.


## Adding State: Score

Kloppy comes with several built-in state builders, including `score`. Let’s use this to enrich the dataset:

```python
dataset = dataset.add_state('score')
print(dataset.events[0].state)
```

This prints:

```
{'score': Score(home=0, away=0)}
```

Each event now includes the current score. As the match progresses, the `score` object is updated automatically when a goal is scored.

To illustrate how this is useful, we’ll look at shots taken during the match:

```python
dataset = dataset.filter(lambda event: event.event_type == EventType.SHOT)
shots = dataset.events
for shot in shots:
    print(shot.state['score'], shot.player.team, '-', shot.player, '-', shot.result)
```

### Filtering Shots by Score

Let’s say we want to analyze shots only when the home team is leading by 2 or more goals. First, convert the dataset to a DataFrame:

```python
dataframe = dataset.to_df(
    "*",
    home_score=lambda event: event.state['score'].home,
    away_score=lambda event: event.state['score'].away
)
```

Now filter:

```python
dataframe[dataframe['home_score'] - dataframe['away_score'] >= 2]
```


## Adding State: Lineup

The `lineup` state allows you to know which players are on the pitch at each moment. Let’s use it to analyze events involving a specific player—Arturo Vidal:

```python
from kloppy import statsbomb

dataset = statsbomb.load_open_data()
home_team, away_team = dataset.metadata.teams

arturo_vidal = home_team.get_player_by_id(8206)
dataframe = (
    dataset
    .add_state('lineup')
    .filter(lambda event: arturo_vidal in event.state['lineup'].players)
    .to_df()
)
print(f"time on pitch: {dataframe['timestamp'].max() - dataframe['timestamp'].min()} seconds")
```

### Comparing Team Passing With and Without Vidal

```python
dataframe = (
    dataset
    .add_state('lineup')
    .filter(lambda event: event.event_type == EventType.PASS and event.team == home_team)
    .to_df(
        "*",
        vidal_on_pitch=lambda event: arturo_vidal in event.state['lineup'].players
    )
)

dataframe = dataframe.groupby(['vidal_on_pitch'])['success'].agg(['sum', 'count'])
dataframe['percentage'] = dataframe['sum'] / dataframe['count'] * 100
print(dataframe)
```


## Adding State: Formation

Let’s add formation data to all shots:

```python
from kloppy import statsbomb
from kloppy.domain import EventType

dataset = statsbomb.load_open_data()

dataframe = (
    dataset
    .add_state('formation')
    .filter(lambda event: event.event_type == EventType.SHOT)
    .to_df(
        "*",
        Team=lambda event: str(event.team),
        Formation=lambda event: str(
            event.state['formation'].home 
            if event.team == dataset.metadata.teams[0] 
            else event.state['formation'].away
        )
    )
)
```

### Shot Efficiency by Formation

```python
dataframe_stats = (
    dataframe
    .groupby(['Team', 'Formation'])['success']
    .agg(['sum', 'count'])
)
dataframe_stats['Percentage'] = dataframe_stats['sum'] / dataframe_stats['count'] * 100
dataframe_stats.rename(columns={'sum': 'Goals', 'count': 'Shots'})
```

This allows you to evaluate shot success depending on the team’s formation at the time of the shot.
