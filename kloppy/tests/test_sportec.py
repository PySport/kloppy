from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy.domain import (
    Provider,
    Orientation,
    Point,
    SetPieceType,
    ShotResult,
    BodyPart,
    DatasetType,
    BallState,
    Point3D,
    PositionType,
    OfficialType,
    Official,
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

        assert len(dataset.events) == 29
        assert dataset.events[28].result == ShotResult.OWN_GOAL

        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == datetime(
            2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[0].end_timestamp == datetime(
            2020, 6, 5, 19, 16, 24, 0, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == datetime(
            2020, 6, 5, 19, 33, 27, 10000, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[1].end_timestamp == datetime(
            2020, 6, 5, 20, 23, 18, 0, tzinfo=timezone.utc
        )

        # Check the timestamps
        assert dataset.events[0].timestamp == timedelta(seconds=0)
        assert dataset.events[1].timestamp == timedelta(seconds=3.123)
        assert dataset.events[25].timestamp == timedelta(seconds=0)

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "DFL-OBJ-00001D"
        assert player.jersey_no == 1
        assert str(player) == "A. Schwolow"
        assert player.starting_position == PositionType.Goalkeeper

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

        assert dataset.events[0].coordinates == Point(0.5641, 0.0)

    def test_pass_receiver_coordinates(
        self, event_data: Path, meta_data: Path
    ):
        """Pass receiver_coordinates must match the X/Y-Source-Position of next event"""
        dataset = sportec.load_event(
            event_data=event_data, meta_data=meta_data
        )

        first_pass = dataset.find("pass")
        assert first_pass.receiver_coordinates != first_pass.next().coordinates
        assert first_pass.receiver_coordinates == Point(
            x=0.7775, y=0.43073529411764705
        )


class TestSportecTrackingData:
    """
    Tests for loading Sportec tracking data.
    """

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def raw_data_referee(self, base_dir) -> str:
        return base_dir / "files/sportec_positional_w_referee.xml"

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
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=400
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=400 + 2786.2
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=4000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=4000 + 2996.68
        )
        assert len(dataset.metadata.officials) == 4

    def test_load_frames(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=False,
        )
        home_team, away_team = dataset.metadata.teams

        assert dataset.frames[0].timestamp == timedelta(seconds=0)
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
                assert frame.timestamp == timedelta(
                    seconds=0
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
        assert len(dataset.records[2].players_data.keys()) == 1

    def test_limit_sample(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
            limit=100,
        )
        assert len(dataset.records) == 100

        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
            limit=100,
            sample_rate=(1 / 2),
        )
        assert len(dataset.records) == 100

    def test_enriched_metadata(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )

        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(
                2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
            )

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "30"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "DFL-MAT-003BN1"

        home_coach = dataset.metadata.home_coach
        if home_coach:
            assert isinstance(home_coach, str)
            assert home_coach == "C. Streich"

        away_coach = dataset.metadata.away_coach
        if away_coach:
            assert isinstance(away_coach, str)
            assert away_coach == "M. Rose"

    def test_referees(self, raw_data_referee: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data_referee,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )
        assert len(dataset.metadata.officials) == 4

        assert (
            Official(
                official_id="42",
                name="Pierluigi Collina",
                role=OfficialType.MainReferee,
            ).role.value
            == "Main Referee"
        )

        assert (
            Official(
                official_id="42",
                name="Pierluigi Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Pierluigi Collina"
        )
        assert (
            Official(
                official_id="42",
                first_name="Pierluigi",
                last_name="Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Pierluigi Collina"
        )
        assert (
            Official(
                official_id="42",
                last_name="Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Collina"
        )
        assert (
            Official(official_id="42", role=OfficialType.MainReferee).full_name
            == "main_referee_42"
        )
        assert Official(official_id="42").full_name == "official_42"
