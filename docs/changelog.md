# Changelog

Find out all changes between different kloppy versions

## 3.1.1 (2022-02-20)

Pull requests merged:

- Add end coordinates for incomplete passes in to_pandas ([#131](https://github.com/PySport/kloppy/pull/131))

## 3.1.0 (2022-01-28)

Pull requests merged:

- Improve contribution guide ([#123](https://github.com/PySport/kloppy/pull/123))
- Fix extraction of foul committed events ([#126](https://github.com/PySport/kloppy/pull/126))
- Add formation statebuilder + read opta/statsbomb formation events ([#125](https://github.com/PySport/kloppy/pull/125))

## 3.0.0 (2021-12-21)

Pull request merged:

- Implement simpler api ([#118](https://github.com/PySport/kloppy/pull/118))

## 2.3.0 (2021-12-03)

Pull request merged:

- Opta serializer improvements ([#119](https://github.com/PySport/kloppy/pull/119))

## 2.2.2 (2021-11-10)

- Don't break when wyscout doesn't include end position of shot/pass

## 2.2.1 (2021-10-31)

- Fix import load_second_spectrum_tracking_data

## 2.2.0 (2021-10-31)

Pull request merged:

- Second Spectrum deserializer ([#106](https://github.com/PySport/kloppy/pull/106))
- Datafactory event deserializer ([#108](https://github.com/PySport/kloppy/pull/108))
- Add distance and speed to frames as well as extra data when available ([#109](https://github.com/PySport/kloppy/pull/109))
- Documentation updates ([#110](https://github.com/PySport/kloppy/pull/110), [#111](https://github.com/PySport/kloppy/pull/111))

## 2.1.0 (2021-08-22)

Pull request merged:

- Add pass type qualifier for opta pass events ([#104](https://github.com/PySport/kloppy/pull/104))

## 2.0.0 (2021-08-11)

Pull request merged:

- Default normalization of coordinates ([#87](https://github.com/PySport/kloppy/pull/87))
- Add missing statsbomb shot outcome values ([#102](https://github.com/PySport/kloppy/pull/102))

## 1.7.0 (2021-07-01)

Pull request merged:

- Include all event qualifiers ([#99](https://github.com/PySport/kloppy/pull/99))
- EPTS: Accept non int ProviderParameters ([#101](https://github.com/PySport/kloppy/pull/101))

## 1.6.1 (2021-06-25)

Pull request merged:

- Modify etps serializer so that it accepts files with no ball z ([#100](https://github.com/PySport/kloppy/pull/100))
- Add ball_z to skillcornertrackingserializer ([#98](https://github.com/PySport/kloppy/pull/98))

## 1.6.0 (2021-05-27)

Pull request merged:

- SkillCorner Serializer ([#90](https://github.com/PySport/kloppy/pull/90))
- Include z-coordinate for ball ([#93](https://github.com/PySport/kloppy/pull/93))
- XML Serializer ([#96](https://github.com/PySport/kloppy/pull/96))
- Add some presentation files ([#95](https://github.com/PySport/kloppy/pull/95))


## 1.5.2 (2021-03-12)

Pull request merged:

- Add Wyscout dataset ([#88](https://github.com/PySport/kloppy/pull/88))


## 1.5.1 (2020-12-23):

Pull request merged:

- Fix for setup ([#80](https://github.com/PySport/kloppy/pull/80))

## 1.5.0 (2020-12-23)
Pull requests merged:

- Add length and width to PitchDimensions ([#77](https://github.com/PySport/kloppy/pull/77))
- Wyscout event data serializer ([#79](https://github.com/PySport/kloppy/pull/79))

## 1.4.2 - 1.4.4 (2020-11-24)

Bugfix:

- Fix for sportec BlockedShot
- Fix sequences reset at set pieces ([#76](https://github.com/PySport/kloppy/pull/76))
- Add pytz to dependencies

## 1.4.1 (2020-11-19)

Bugfix:

- Sportec: insert BALL_OUT event before corner kick  

## 1.4.0 (2020-11-19)
Pull requests merged:

- Improve sequence definition based on latest added generic events ([#75](https://github.com/PySport/kloppy/pull/75))
- refactor: improve code readability on kloppy-query cli s([#74](https://github.com/PySport/kloppy/pull/74))
- refactor: single github workflow ([#73](https://github.com/PySport/kloppy/pull/73))
- Sportec serializer ([#70](https://github.com/PySport/kloppy/pull/71))


## 1.3.0 (2020-10-06)
Pull requests merged:

- Add distance to point ([#63](https://github.com/PySport/kloppy/pull/63))
- Add additional event types and introduce qualifiers ([#70](https://github.com/PySport/kloppy/pull/70))

## 1.2.1 (2020-09-22)
Bugfix:

- Don't crash when TRACAB contains unknown team id

## 1.2.0 (2020-09-08)
Github issues closed:

- Enrich events with state ([#48](https://github.com/PySport/kloppy/issues/48))

Other pull requested merged:

- Chaining of methods ([#59](https://github.com/PySport/kloppy/pull/59))

## 1.1.1 (2020-09-01)
Github issues closed:

- to_pandas fails for Opta data when trying to read player_id ([#57](https://github.com/PySport/kloppy/issues/57)

Other pull requests merged:

- Fix error in naming of inputs to metrica json serializer in helper ([#56](https://github.com/PySport/kloppy/pull/56))

## 1.1.0 (2020-08-07)
Github issues closed:

- Add provider to dataset ([#36](https://github.com/PySport/kloppy/issues/36))
- Adding a data type type to the datasets ([#45](https://github.com/PySport/kloppy/issues/45))

Other pull requests merged:

- Code formatting & typos in docs ([#39](https://github.com/PySport/kloppy/pull/39), [#40](https://github.com/PySport/kloppy/pull/40))
- Add Metrica Json event serializer ([#44](https://github.com/PySport/kloppy/pull/44))
- Infer ball_owning_team from Opta events ([#49](https://github.com/PySport/kloppy/pull/49)

## 1.0.0 (2020-07-26)
In this major release we introduce metadata. The metadata is part of a dataset and can be accessed via `Dataset.metadata`.
There are a couple of breaking changes:

1. All attributes except `records` / `frames` are moved from `Dataset` to `Metadata` class.
2. All `position` properties are renamed to `coordinates`.
3. The `players_coordinates` property is indexed by `Player` instances instead of by `jersey_number` strings.
4. On the `Event` class the `player_jersey_number` is replaced by `player` which is a `Player` instance.
5. `to_pandas` changes:
    - `player_jersey_number` is replaced by `player_id`
    - `team` is replaced by `team_id`
    - `position_*` is renamed to `coordinates_*`
    - `player_<home/away>_<jersey_no>_x` is renamed to `<player_id>_x`

Github issues closed:
- Website for project ([#27](https://github.com/PySport/kloppy/issues/27), [#30](https://github.com/PySport/kloppy/issues/30))
- Metadata model ([#3](https://github.com/PySport/kloppy/issues/3))
- IDs instead of [home, away, shirt_number] ([#17](https://github.com/PySport/kloppy/issues/17))

Other pull requests merged:
- Fix docs ([#35](https://github.com/PySport/kloppy/pull/35))

## 0.6.2 (2020-07-23)
- Fix to_pandas for Opta event data

## 0.6.1 (2020-07-02)
- Fix in readme (@rjtavares)
- Add additional_columns to to_pandas (@rjtavares)

## 0.6.0 (2020-06-18)
- Add Opta event serializer
- Fix for event pattern matching for nested captures
- Fix for event pattern matching when multiple paths can match
- Improved ball_recovery example

## 0.5.3 (2020-06-16)
- Add code formatting and contributing guide (@dmallory42)
- Add support for python 3.6

## 0.5.2 (2020-06-13)
- Fix Transformer when ball position is not set (@benoitblanc)
- Fix for working with periods in EPTS Serializer (@bdagnino)

## 0.5.1 (2020-06-13)
- Add stats in json/text format to kloppy-query
- Add show-events to kloppy-query to print all events in the matches
- Change kloppy-query to make it possible to run without an output file

## 0.5.0 (2020-06-13)
- Add pattern matching based on regular expressions
- Add kloppy-query: command line tool to search for patterns

## 0.4.1 (2020-06-05)
- Fix for StatsBomb Serializer when location contains z coordinate

## 0.4.0 (2020-06-02)
- Add StatsBomb event Serializer
- Some fixes in readme
- Refactor some code to get cleaner code
- Pass a logger to performance_logging instead of print to stdout
- Minor fixes to datasets loader

## 0.3.0 (2020-05-15)
- Add FIFA EPTS Tracking Serializer
- Add some examples
- Add datasets loader to directly load dataset from your python code
- Add limit argument to all loaders

## 0.2.1 (2020-05-12)
- Add some helpers functions to directly load a dataset by filenames

## 0.2.0 (2020-05-05)
- Change interface of TrackingDataSerializer
- Add Metrica Tracking Serializer including automated tests
- Cleanup some import statements

## 0.1.0 (2020-04-23)
- Initial release (TRACAB)
