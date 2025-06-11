# Adding a new data provider to kloppy

This document will outline the basics of how to get started on adding a new Event data provider or a new Tracking data provider.

## General

### Deserialization

**Kloppy** has two types of datasets, namely `EventDataset` and `TrackingDataset`. These datasets are generally constructed from two files: a file containing raw (event/tracking) data and a meta data file containing pitch dimensions, squad, match and player information etc.

The creation of these standardized datasets is called **"deserialization"**.

> "Deserialization is the process of converting a data structure or object state stored in a format like JSON, XML, or a binary format into a usable object in memory." [$^1$](https://www.imperva.com/learn/application-security/deserialization/)

Due to its vast amount of available open data we'll use the [**SportecEventDeserializer**](https://github.com/PySport/kloppy/blob/master/kloppy/infra/serializers/event/sportec/deserializer.py) as our guide for deserializing event data and we'll use the [**SkillCornerDeserializer**](https://github.com/PySport/kloppy/blob/master/kloppy/infra/serializers/tracking/skillcorner.py) as an example of how to deserialize tracking data, because it has open data available and because it is provided in the most common format for tracking data delivery ("json").

### File Structure

Adding a new provider requires the creation of _at least_ four files:

- The [**deserializer file**](#deserializer-file), located in `kloppy/kloppy/infra/serializers/{event | tracking}/{provider_name}/deserializer.py`. <small>([Sportec Deserializer File](https://github.com/PySport/kloppy/blob/master/kloppy/infra/serializers/event/sportec/deserializer.py))</small>
- The [**loader file**](#loader-file), located in `kloppy/_providers/{provider_name}.py`. <small>([Sportec Loader File](https://github.com/PySport/kloppy/blob/master/kloppy/_providers/sportec.py))</small>
- The [**initialization file**](#initialization-file), located in `kloppy/{provider_name}.py`. <small>([Sportec Initialization File](https://github.com/PySport/kloppy/blob/master/kloppy/sportec.py))</small>
- The [**unit test file**](#unit-tests), located in `kloppy/tests/test_{provider_name}.py`. <small>([Sportec Unit Test File](https://github.com/PySport/kloppy/blob/master/kloppy/tests/test_sportec.py))</small>

#### Deserializer File

The **deserializer file** contains the main `{ProviderName}Deserializer` class and an associated `{ProviderName}Inputs` classes. As examplified below:

```python
class SportecEventDataInputs(NamedTuple):
    meta_data: IO[bytes]
    event_data: IO[bytes]


class SportecEventDataDeserializer(
    EventDataDeserializer[SportecEventDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    def deserialize(self, inputs: SportecEventDataInputs) -> EventDataset:
        with performance_logging("load data", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())
            event_root = objectify.fromstring(inputs.event_data.read())
```

<small>Source: [Sportec Deserializer File](https://github.com/PySport/kloppy/blob/master/kloppy/infra/serializers/event/sportec/deserializer.py)</small>

#### Loader File

The **loader file** contains one or more loading functions, grouped by provider. For example if a data provider provides both event and tracking data as well as open data for both this file will contain:

- `load_event()`
- `load_tracking()`
- `load_open_event_data()`
- `load_open_tracking_data()`

These functions look something like this:

```python
def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    etc...
```

<small>Source: [Sportec Loader File](https://github.com/PySport/kloppy/blob/master/kloppy/_providers/sportec.py)</small>

#### Initialization File

To easily use kloppy (i.e. `from kloppy import provider_name`) each provider has this file. It should contain the following, for each of loading functions in the **loader file**:

```python
from ._providers.provider_name import (
    load_event,
    load_tracking,
    load_open_event_data,
    load_open_tracking_data,
)

__all__ = [
    "load_event",
    "load_tracking",
    "load_open_event_data",
    "load_open_tracking_data",
]
```

<small>Source: [Sportec Initialization File](https://github.com/PySport/kloppy/blob/master/kloppy/sportec.py)</small>

### Unit Tests

Before finalizing your new provider deserializer, you'll have to add automated tests. These tests are meant to ensure correct behaviour and they should help catch any (breaking) changes in the future.

Kloppy using [_pytest_](https://docs.pytest.org/en/stable/) for their unit testing.

For example:

```python
import pytest
from kloppy import sportec


class TestSportecEventData:
    """"""

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/sportec_events.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta.xml"

    def test_correct_event_data_deserialization(
        self, event_data: Path, meta_data: Path
    ):
        dataset = sportec.load_event(
            event_data=event_data,
            meta_data=meta_data,
            coordinates="sportec",
        )

        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2
```

<small>Source: [Sportec Unit Test File](https://github.com/PySport/kloppy/blob/master/kloppy/tests/test_sportec.py)</small>

### Code Formatting

**Kloppy** uses the [_black_](https://black.readthedocs.io/en/stable/) code formatter to ensure all code conforms to a specified format. It is necessary to
format the code using _black_ prior to committing. There are two ways to do this, one is to manually run the command
`black .` (to run `black` on all `.py` files (or, `black <filename.py>` to run on a specific file).

Alternatively, it is possible to setup a Git hook to automatically run _black_ upon a `git commit` command. To do this,
follow these instructions:

- Execute the command `pre-commit install` to install the Git hook.
- When you next run a `git commit` command on the repository, _black_ will run and automatically format any changed files. _Note_: if _black_ needs to re-format a file, the commit will fail, meaning you will then need to execute `git add .` and `git commit` again to commit the files updated by _black_.

### Updating Documentation

**Kloppy** uses [_MkDocs_](https://www.mkdocs.org/) to create documenation. The documentation primarily consists of Markdown files.

To install all documentation related dependancies run:

```cmd
python -m pip install -r docs-requirements.txt
```

To open the documentation in http://127.0.0.1:8000/ run:

```cmd
mkdocs serve
```

Add any changes you're committing via [Pull Request](#creating-pull-request) to the documentation to keep it up-to-date.

### Creating Pull Request

To cleanly share the additions made to kloppy you need to make what is called a Pull Request (PR). To do this cleanly it is advised to do the following:

1. If you start for the first time, create a ["fork"](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) of the kloppy repository.
2. [Clone](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) the newly created fork locally.
3. Create a new branch using something like `git checkout -b <branch_name>`
4. After you have made your changes in this newly created branch:
   - Run `pytest kloppy/tests` or `pytest kloppy/tests/test_{provider_name}.py` to ensure all tests complete successfully.
   - [Update the documentation](#updating-documentation) with any and all changes.
   - Run `black <filename>` on all the new files.
   - Run `git add <filename>` on all the new files.
   - Run `git commit -m "<some message>"`
   - Push the changes to your remote reposity with `git push` or `git push --set-upstream origin` if you're pushing for the first time.
5. Now, go to [kloppy > Pull Requests](https://github.com/PySport/kloppy/pulls) and click the green "New pull request" button.
   - Set base: `master`
   - Set compare: `<branch_name>`
   - Click "Create pull request"
   - Write an exhaustive Pull Request message to inform everything you've contributed.
6. Finally, after the PR has been completed automated tests will run on GitHub to make sure eveything (still) functions as expected.

## Event Data

### Files

See [1.2 File Structure](#file-structure) for more information.

#### Loading File

The loading file should have a function `load` (or `load_event` if this data provider also provides tracking data).

This function takes at least:

- One or more [`FileLike`][kloppy.io.FileLike] objects, generally a file of event data and a meta data file.
- `event_types`, an optional list of strings to filter the dataset at load time. (e.g. event_types can be `["pass", "shot"]`) these string values relate to the [`EventType`][kloppy.domain.EventType] class.
- `coordinates`, an optional string that relates to [`Provider`][kloppy.domain.Provider] and their associated [Coordinate Systems][kloppy.domain.CoordinateSystem]. (e.g. coordinates can be `"secondspectrum"` or `"statsbomb"`).
- `event_factory`, an optional `EventFactory`.

Within the function we instantiate the `ProviderNameDeserialzer` that we import from `from kloppy.infra.serializers.event.{new_provider}` alongside the `ProviderNameInputs`.

Note: The "opening" of the file is handled by `FileLike` and `with open_as_file()` as shown below.

```python
from typing import Optional, List

from kloppy.domain import EventDataset, EventFactory
from kloppy.infra.serializers.tracking.new_provider import (
    ProviderNameDeserializer,
    ProviderNameInputs,
)
from kloppy.io import FileLike, open_as_file

def load(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    [insert docstrings]
    """
    deserializer = ProviderNameDeserializer(
        coordinate_system=coordinates,
        event_factory=event_factory
        or get_config("event_factory")
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return deserializer.deserialize(
            inputs=ProviderNameInputs(
                event_data=event_data_fp,
                meta_data=meta_data_fp,
            )
        )
```

#### Deserialization File

- Create a `ProviderNameDataInputs` class
- Create a `ProviderNameEventDataDeserializer`
- Add a new provider to the `Provider` class in `kloppy.domain.models.common.py` set that new provider in the `provider` property in the `ProviderNameEventDataDeserializer`

```python
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer

class ProviderNameDataInputs(NamedTuple):
    event_data: IO[bytes]
    meta_data: IO[bytes]


class ProviderNameEventDataDeserializer(
    EventDataDeserializer[ProviderNameDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.PROVIDER_NAME

    def deserialize(self, inputs: ProviderNameDataInputs) -> EventDataset:
        with performance_logging("load data", logger=logger):
            match_root = # read inputs.meta_data as xml, json etc.
            event_root = # read inputs.event_root as xml, json etc.

```

Create a `deserialize` method that takes the `ProviderNameDataInputs` as inputs. Within the `deserialize` method we do two high level actions:

1. [Parse meta data items into a `Metadata` object.](#parsing-metadata)
2. [Parse events into an `events` list.](#parsing-events)

These two will ultimately form the `EventDataset` that is returned from the `deserialize` method. i.e.

```python
return EventDataset(
    metadata=metadata,
    records=events,
)
```

### EventDataset

#### Parsing Metadata

Use the meta data and event data feeds to parse:

- `teams` as `Team` objects in a list `[home_team, away_team]`
- `periods` a list of `Period` objects (don't forget about optional extra time.)
  - Each period has an `id` (1, 2, 3, 4)
  - Each period has a `start_timestamp` and `end_timestamp` of type `timedelta`. This `timedelta` object describes the time elapsed since the start of the period in question.
- `pitch_dimensions` is a `PitchDimensions`
- `orientation`. Identify the direction of play (`Orientation`) (e.g. `orientation = Orientation.ACTION_EXECUTING_TEAM`)
- `flags`. Indicate if our dataset contains information on who the ball owning team is and/or if we know ball state.
  - For example: `flags = DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM` or `flags = ~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM`)
- `provider`. Update the `Provider` enum class and add the new provider.
- `coordinate_system`. A `CoordinateSystem` object that contains information like `pitch_length`, `vertical_orientation` etc. Create a new `ProviderNameCoordinateSytem` class that inherits from `ProviderCoordinateSystem`.
- Optional metadata such as:
  - `score` (`Score`)
  - `frame_rate` (`float`)
  - `date` (`datetime`)
  - etc.

#### Parsing Events

Before parsing the events order them by their timestamp to create a chronological ordering.

Now, for each possible `EventType` create an `event` by using the built in event factory. This `EventFactory` is inherited into the `ProviderNameDeserializer` through the `EventDataDeserializer` as described [above](#deserialization-file).

Parsing each individual event type, requires some `generic_events_kwargs` (dict) that contains information such as player, team (of event executing player) etc. Additionally, it also contains the full `raw_event`. This ensure that no information is actually lost while parsing an event.

```python
generic_event_kwargs = dict(
    # from DataRecord
    period=period,
    timestamp=timestamp - period.start_timestamp,
    ball_owning_team=None,
    ball_state=BallState.ALIVE,
    # from Event
    event_id=event_chain["Event"]["EventId"],
    coordinates=_parse_coordinates(event_chain["Event"]),
    raw_event=flatten_attributes,
    team=team,
    player=player,
)
```

Now, we combine these `generic_event_kwargs` and our event specific `{someEvent}_event_kwargs` and use `self.event_factory.build_{someEvent}` to consistantly churn out events of the same structure.

```python
event_name, event_attributes = event_chain.popitem()
if event_name in SPORTEC_SHOT_EVENT_NAMES:
    shot_event_kwargs = _parse_shot(
        event_name=event_name, event_chain=event_chain
    )
    event = self.event_factory.build_shot(
        **shot_event_kwargs,
        **generic_event_kwargs,
    )
```

Finally, each `event` is appended to the `events` list.

#### Deserialization Checklist

- Make sure the `FileLike` objects are processed correctly in the deserializer. This means opening the files in the [Loader File](#loader-file) using `open_as_file`.
- Create variables for each string representation of events, to make the code less error prone. e.g.
  - `SPORTEC_EVENT_NAME_OWN_GOAL = "OwnGoal"`
- Don't forget about different types (i.e. `SetPieceType`, `CardType`, `PassType`, `BodyPartType`, `GoalKeeperActionType` or `DuelType`)
- Don't forget about different result types (i.e. `PassResult`, `ShotResult`, `TakeOnResult`, `CarryResult`, `DuelResult`, `InterceptionResult`)
- Don't forget to include own goals, yellow and red cards, extra time, penalties etc.
- Map provider specific position labels to Kloppy standardized position labels, e.g.:
  ```python
  """
  Here the 'str' keys are the position labels as provided by the data provider (in this case they are German labels)
  """
  position_types_mapping: Dict[str, PositionType] = {
      "TW": PositionType.Goalkeeper,
      "IVR": PositionType.RightCenterBack,
      "IVL": PositionType.LeftCenterBack,
      ...
      "OLM": PositionType.LeftMidfield,
      "RA": PositionType.RightWing,
      "LA": PositionType.LeftWing,
  }
  ```
- When converting these position labels use `position_types_mapping.get(provider_position_label, PositionType.Unknown)`. This will ensure even if we have a missing position label our newly built deserializer every position will be of type `PositionType`.
- `deserialize` returns an `EventDataset(metadata=metadata, records=events)`
- `Period` `start_timestamp` is of type `timedelta`. This time delta relates to the start of a period (i.e. each period starts at `0`)
- Parse `Substitutions` seperately from `PlayerOn` and `PlayerOff` (if this is provided by the provider).
  - Player Off / Player On events represent players (temporarily) leaving the pitch (e.g. injury treatment, red card)
  - Substitutions represent a one for one exchange of two players.
- Update the `event-spec.yml` file in the Documentation to cover:
  - parsed. If this event is now included in the event data parser.
  - not implemented. If this event is provided by the data provider, but is currently not included in kloppy.
  - not supported. If this event is not provided by the data provider.
  - unknown. If the status is unknown.
  - inferred. When an event is inferred from other events (e.g. Ball out events for some providers)
