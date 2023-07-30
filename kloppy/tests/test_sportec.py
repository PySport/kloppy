from pathlib import Path

import pytest

from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    SetPieceType,
    BodyPart,
    DatasetType,
    BallState,
    Point3D,
)

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

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        assert len(dataset.events) == 28
        assert dataset.metadata.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=1591381800.21,
            end_timestamp=1591384584.0,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=1591385607.01,
            end_timestamp=1591388598.0,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "DFL-OBJ-00001D"
        assert player.jersey_no == 1
        assert str(player) == "A. Schwolow"
        assert player.position.position_id is None
        assert player.position.name == "TW"

        # Check the qualifiers
        assert dataset.events[25].qualifiers[0].value == SetPieceType.KICK_OFF
        assert dataset.events[16].qualifiers[0].value == BodyPart.RIGHT_FOOT
        assert dataset.events[24].qualifiers[0].value == BodyPart.LEFT_FOOT
        assert dataset.events[26].qualifiers[0].value == BodyPart.HEAD

        assert dataset.events[0].coordinates == Point(56.41, 68.0)

    def test_correct_normalized_event_data_deserialization(
        self, event_data: Path, meta_data: Path
    ):
        dataset = sportec.load_event(
            event_data=event_data, meta_data=meta_data
        )

        assert dataset.events[0].coordinates == Point(0.5640999999999999, 1)


class TestSportecTrackingData:
    """
    Tests for loading Sportec tracking data.
    """

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta.xml"

    def test_load_metadata(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data, meta_data=meta_data, coordinates="sportec"
        )

        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.metadata.periods) == 2

    def test_load_frames(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=False,
        )
        home_team, away_team = dataset.metadata.teams

        assert dataset.frames[0].timestamp == 0.0
        assert dataset.frames[0].ball_owning_team == away_team
        assert dataset.frames[0].ball_state == BallState.DEAD
        assert dataset.frames[0].ball_coordinates == Point3D(
            x=2.69, y=0.26, z=0.06
        )
        assert dataset.frames[1].ball_speed == 65.59

        assert dataset.frames[1].ball_owning_team == home_team
        assert dataset.frames[1].ball_state == BallState.ALIVE

        player_lilian = away_team.get_player_by_id("DFL-OBJ-002G3I")
        player_data = dataset.frames[0].players_data[player_lilian]

        assert player_data.coordinates == Point(x=0.35, y=-25.26)

        # We don't load distance right now as it doesn't
        # work together with `sample_rate`: "The distance covered from the previous frame in cm"
        assert player_data.distance is None

        # Appears first in 27th frame
        player_bensebaini = away_team.get_player_by_id("DFL-OBJ-002G5S")
        assert player_bensebaini not in dataset.frames[0].players_data
        assert player_bensebaini in dataset.frames[26].players_data

        # Contains all 3 players
        assert len(dataset.frames[35].players_data) == 3
        assert len(dataset) == 202

        second_period = dataset.metadata.periods[1]
        for frame in dataset:
            if frame.period == second_period:
                assert (
                    frame.timestamp == 0
                ), "First frame must start at timestamp 0.0"
                break
        else:
            # No data found in second half
            assert False

    def test_load_only_alive_frames(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )
        assert len(dataset) == 199
