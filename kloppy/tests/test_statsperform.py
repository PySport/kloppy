from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy import statsperform
from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    OptaCoordinateSystem,
    Orientation,
    PassResult,
    Point,
    Point3D,
    PositionType,
    Provider,
    SportVUCoordinateSystem,
    Time,
    TrackingDataset,
)


@pytest.fixture(scope="module")
def event_metadata_xml(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_event_ma1.xml"


@pytest.fixture(scope="module")
def event_metadata_json(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_event_ma1.json"


@pytest.fixture(scope="module")
def event_data_xml(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_event_ma3.xml"


@pytest.fixture(scope="module")
def event_data_json(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_event_ma3.json"


@pytest.fixture(scope="module")
def tracking_metadata_xml(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_tracking_ma1.xml"


@pytest.fixture(scope="module")
def tracking_metadata_json(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_tracking_ma1.json"


@pytest.fixture(scope="module")
def tracking_data(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_tracking_ma25.txt"


@pytest.fixture(scope="module", params=["xml", "json"])
def tracking_dataset(
    request: pytest.FixtureRequest,
    tracking_metadata_xml: Path,
    tracking_metadata_json: Path,
    tracking_data: Path,
) -> TrackingDataset:
    return statsperform.load_tracking(
        ma1_data=(
            tracking_metadata_xml
            if request.param == "xml"
            else tracking_metadata_json
        ),
        ma25_data=tracking_data,
        tracking_system="sportvu",
        only_alive=False,
        coordinates="sportvu",
    )


@pytest.fixture(scope="module", params=["xml", "json"])
def event_dataset(
    request: pytest.FixtureRequest,
    event_metadata_xml: Path,
    event_metadata_json: Path,
    event_data_xml: Path,
    event_data_json: Path,
) -> EventDataset:
    return statsperform.load_event(
        ma1_data=(
            event_metadata_xml
            if request.param == "xml"
            else event_metadata_json
        ),
        ma3_data=event_data_xml if request.param == "xml" else event_data_json,
        coordinates="opta",
    )


class TestStatsPerformMetadata:
    """Tests related to deserializing the MA1 meta data feed."""

    def test_provider(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.metadata.provider == Provider.STATSPERFORM

    def test_orientation(self, event_dataset: EventDataset):
        assert event_dataset.metadata.coordinate_system == OptaCoordinateSystem(
            # StatsPerform does not provide pitch dimensions
            pitch_length=None,
            pitch_width=None,
        )

    def test_teams(self, tracking_dataset: TrackingDataset):
        home_team = tracking_dataset.metadata.teams[0]
        home_player = home_team.players[2]

        assert home_player.player_id == "5g5wwp5luxo1rz1kp6chvz0x6"
        assert tracking_dataset.records[0].players_coordinates[
            home_player
        ] == Point(x=68.689, y=39.75)
        assert home_player.starting_position == PositionType.LeftCenterBack
        assert home_player.jersey_no == 32
        assert home_player.starting
        assert home_player.team == home_team

        away_team = tracking_dataset.metadata.teams[1]
        away_player = away_team.players[3]
        assert away_player.player_id == "72d5uxwcmvhd6mzthxuvev1sl"
        assert tracking_dataset.records[0].players_coordinates[
            away_player
        ] == Point(x=30.595, y=44.022)
        assert away_player.starting_position == PositionType.RightCenterBack
        assert away_player.jersey_no == 2
        assert away_player.starting
        assert away_player.team == away_team

        away_substitute = away_team.players[15]
        assert away_substitute.jersey_no == 18
        assert away_substitute.starting_position is None
        assert not away_substitute.starting
        assert away_substitute.team == away_team

        home_gk = home_team.get_player_by_id("6wfwy94p5bm0zv3aku0urfq39")
        assert home_gk.first_name == "Benjamin Pascal"
        assert home_gk.last_name == "Lecomte"

    def test_periods(self, tracking_dataset: TrackingDataset):
        assert len(tracking_dataset.metadata.periods) == 2
        assert tracking_dataset.metadata.periods[0].id == 1
        assert tracking_dataset.metadata.periods[
            0
        ].start_timestamp == datetime(
            2020, 8, 23, 11, 0, 10, tzinfo=timezone.utc
        )
        assert tracking_dataset.metadata.periods[0].end_timestamp == datetime(
            2020, 8, 23, 11, 48, 15, tzinfo=timezone.utc
        )

        assert tracking_dataset.metadata.periods[1].id == 2
        assert tracking_dataset.metadata.periods[
            1
        ].start_timestamp == datetime(
            2020, 8, 23, 12, 6, 22, tzinfo=timezone.utc
        )
        assert tracking_dataset.metadata.periods[1].end_timestamp == datetime(
            2020, 8, 23, 12, 56, 30, tzinfo=timezone.utc
        )

    def test_enriched_metadata(self, tracking_dataset: TrackingDataset):
        date = tracking_dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(2020, 8, 23, 0, 0, tzinfo=timezone.utc)

        game_week = tracking_dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "1"

        game_id = tracking_dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "7ijuqohwgmplbxdj1625sxwfe"


class TestStatsPerformEvent:
    """Tests related to deserializing the MA3 event data feed.

    See Also:
        kloppy.tests.test_opta.TestOptaEvent
    """

    def test_deserialize_all(self, event_dataset: EventDataset):
        assert event_dataset.metadata.provider == Provider.STATSPERFORM

        assert len(event_dataset.records) == 1643

        substitution_events = event_dataset.find_all("substitution")
        assert len(substitution_events) == 9

        m_wintzheimer = event_dataset.metadata.teams[0].get_player_by_id(
            "aksjicf4keobpav3tuujngell"
        )
        b_jatta = event_dataset.metadata.teams[0].get_player_by_id(
            "3mp7p8tytgkbwi8itxl5mfkrt"
        )

        first_sub = substitution_events[0]

        assert first_sub.time == Time(
            period=event_dataset.metadata.periods[1],
            timestamp=timedelta(seconds=946, microseconds=475000),
        )
        assert first_sub.player == m_wintzheimer
        assert first_sub.replacement_player == b_jatta

    def test_pass_receiver(self, event_dataset: EventDataset):
        """It should impute the intended receiver of a pass."""
        # Completed passes should get a receiver
        complete_pass = event_dataset.get_event_by_id("2328589789")
        assert (
            complete_pass.receiver_player.player_id
            == "apdrig6xt1hxub1986s3uh1x"
        )
        assert (
            complete_pass.receive_timestamp
            == complete_pass.next_record.timestamp
        )

        # When a pass is challenged the receipt is the next next event
        challenged_pass = event_dataset.get_event_by_id("2328600271")
        assert (
            challenged_pass.receiver_player.player_id
            == "ci4pwzieoc94uj3i1371bsatx"
        )
        assert (
            challenged_pass.receive_timestamp
            == challenged_pass.next_record.next_record.timestamp
        )

        # Passes should be received within 30 seconds
        assert all(
            [
                p.receive_timestamp.total_seconds()
                - p.timestamp.total_seconds()
                < 30
                for p in event_dataset.find_all("pass")
                if p.receive_timestamp is not None
            ]
        )

        # Passes that result in a loss of possession should not have a receiver
        turnover_passes = [
            p
            for p in event_dataset.find_all("pass")
            if p.next_record
            and p.ball_owning_team != p.next_record.ball_owning_team
        ]
        assert all(p.receiver_player is None for p in turnover_passes)

        # Failed passes should not have a receiver
        failed_pass = event_dataset.get_event_by_id("2328591011")
        assert failed_pass.receiver_player is None
        out_pass = event_dataset.get_event_by_id("2328590733")
        assert out_pass.receiver_player is None

        # When a pass is interrupted by a foul the receiver is not set
        fouled_pass = event_dataset.get_event_by_id("2328589929")
        assert fouled_pass.receiver_player is None

        # Deflected passes should not have a receiver
        deflected_pass = event_dataset.get_event_by_id("2328596237")
        assert deflected_pass.receiver_player is None


class TestStatsPerformTracking:
    """Tests related to deserializing tracking data delivered by StatsPerform."""

    def test_orientation(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_framerate(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.metadata.frame_rate == 10.0

    def test_flags(self, tracking_dataset):
        assert tracking_dataset.metadata.flags == DatasetFlag.BALL_STATE

    def test_correct_deserialization_limit_sample(
        self, tracking_data: Path, tracking_metadata_xml: Path
    ):

        tracking_dataset = statsperform.load_tracking(
            ma1_data=tracking_metadata_xml,
            ma25_data=tracking_data,
            tracking_system="sportvu",
            coordinates="sportvu",
            pitch_length=105,
            pitch_width=68,
            limit=50,
        )
        assert len(tracking_dataset.records) == 50

        tracking_dataset = statsperform.load_tracking(
            ma1_data=tracking_metadata_xml,
            ma25_data=tracking_data,
            tracking_system="sportvu",
            coordinates="sportvu",
            pitch_length=105,
            pitch_width=68,
            limit=25,
            sample_rate=(1 / 2),
        )
        assert len(tracking_dataset.records) == 25

    def test_coordinate_system_without_pitch_dimensions(
        self, tracking_data: Path, tracking_metadata_xml: Path
    ):
        tracking_dataset = statsperform.load_tracking(
            ma1_data=tracking_metadata_xml,
            ma25_data=tracking_data,
            tracking_system="sportvu",
            coordinates="sportvu",
        )
        coordinate_system = tracking_dataset.metadata.coordinate_system
        pitch_dimensions = tracking_dataset.metadata.pitch_dimensions
        assert coordinate_system == SportVUCoordinateSystem(
            # StatsPerform does not provide pitch dimensions
            pitch_length=None,
            pitch_width=None,
        )
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max is None
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max is None

    def test_coordinate_system_with_pitch_dimensions(
        self, tracking_data: Path, tracking_metadata_xml: Path
    ):
        tracking_dataset = statsperform.load_tracking(
            ma1_data=tracking_metadata_xml,
            ma25_data=tracking_data,
            tracking_system="sportvu",
            coordinates="sportvu",
            pitch_length=105,
            pitch_width=68,
        )
        coordinate_system = tracking_dataset.metadata.coordinate_system
        pitch_dimensions = tracking_dataset.metadata.pitch_dimensions
        assert coordinate_system == SportVUCoordinateSystem(
            # StatsPerform does not provide pitch dimensions
            pitch_length=105,
            pitch_width=68,
        )
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max == 105
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == 68

    def test_deserialize_all(self, tracking_dataset: TrackingDataset):
        assert len(tracking_dataset.records) == 92

    def test_deserialize_only_alive(
        self, tracking_data: Path, tracking_metadata_xml: Path
    ):
        tracking_dataset = statsperform.load_tracking(
            ma1_data=tracking_metadata_xml,
            ma25_data=tracking_data,
            tracking_system="sportvu",
            only_alive=True,
            coordinates="sportvu",
        )
        assert len(tracking_dataset.records) == 91

    def test_timestamps(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.records[0].timestamp == timedelta(
            seconds=0
        )  # First frame
        assert tracking_dataset.records[20].timestamp == timedelta(
            seconds=2.0
        )  # Later frame
        assert tracking_dataset.records[26].timestamp == timedelta(
            seconds=0
        )  # Second period

    def test_ball_coordinates(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.records[1].ball_coordinates == Point3D(
            x=50.615, y=35.325, z=0.0
        )

    def test_player_coordinates(self, tracking_dataset: TrackingDataset):
        home_player = tracking_dataset.metadata.teams[0].players[2]
        assert tracking_dataset.records[0].players_coordinates[
            home_player
        ] == Point(x=68.689, y=39.750)

    def test_correct_normalized_deserialization(
        self, tracking_data: Path, tracking_metadata_xml: Path
    ):
        tracking_dataset = statsperform.load_tracking(
            ma1_data=tracking_metadata_xml,
            ma25_data=tracking_data,
            tracking_system="sportvu",
            pitch_length=105,
            pitch_width=68,
            only_alive=False,
            coordinates="kloppy",
        )

        assert tracking_dataset.records[1].ball_coordinates == Point3D(
            x=50.615 / 105, y=35.325 / 68, z=0.0
        )

        # Check normalised pitch dimensions
        pitch_dimensions = tracking_dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0.0
        assert pitch_dimensions.x_dim.max == 1.0
        assert pitch_dimensions.y_dim.min == 0.0
        assert pitch_dimensions.y_dim.max == 1.0

        # Pitch dimensions are required to transform coordinates
        with pytest.warns(
            UserWarning,
            match="The pitch dimensions are required to transform coordinates *",
        ):
            statsperform.load_tracking(
                ma1_data=tracking_metadata_xml,
                ma25_data=tracking_data,
                tracking_system="sportvu",
                coordinates="kloppy",
            )
