# Changelog

Find out all changes between different kloppy versions

## 1.0.0
In this major release we introduce metadata. The metadata is part of a dataset and can be accessed via `Dataset.metadata`.
There are a couple of breaking changes:

1. All attributes except `records` / `frames` are moved from `Dataset` to `Metadata` class. 
2. All `position` properties are renamed to `coordinates`. 
3. The the `players_coordinates` property is indexed by `Player` instances instead of by `jersey_number` strings.
4. On the `Event` class the `player_jersey_number` is replaced by `player` which is `Player` instance. 
5. `to_pandas` changes:
    - `player_jersey_number` is replaced by `player_id`
    - `team` is replaced by `team_id
    - `position_*` is renamed to `coordinates_*`
    - `player_<home/away>_<jersey_no>_x` is renamed to `<player_id>_x`

Github issues closed:

- Website for project ([#27](https://github.com/PySport/kloppy/issues/27), [#30](https://github.com/PySport/kloppy/issues/30))
- Metadata model ([#3](https://github.com/PySport/kloppy/issues/3))
- IDs instead of [home, away, shirt_number] ([#17](https://github.com/PySport/kloppy/issues/17))


## 0.6.2
- Fix to_pandas for Opta event data