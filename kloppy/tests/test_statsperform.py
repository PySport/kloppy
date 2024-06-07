from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy import statsperform
from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    OptaCoordinateSystem,
    Orientation,
    Point,
    Point3D,
    Provider,
    SportVUCoordinateSystem,
    TrackingDataset,
)
from kloppy.exceptions import KloppyError


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
        ma1_data=tracking_metadata_xml
        if request.param == "xml"
        else tracking_metadata_json,
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
        ma1_data=event_metadata_xml
        if request.param == "xml"
        else event_metadata_json,
        ma3_data=event_data_xml if request.param == "xml" else event_data_json,
        coordinates="opta",
    )


class TestStatsPerformMetadata:
    """Tests related to deserializing the MA1 meta data feed."""

    def test_provider(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.metadata.provider == Provider.STATSPERFORM

    def test_teams(self, tracking_dataset: TrackingDataset):
        home_team = tracking_dataset.metadata.teams[0]
        home_player = home_team.players[2]
        assert home_player.player_id == "5g5wwp5luxo1rz1kp6chvz0x6"
        assert tracking_dataset.records[0].players_coordinates[
            home_player
        ] == Point(x=68.689, y=39.75)
        assert home_player.position == "Defender"
        assert home_player.jersey_no == 32
        assert home_player.starting
        assert home_player.team == home_team

        away_team = tracking_dataset.metadata.teams[1]
        away_player = away_team.players[3]
        assert away_player.player_id == "72d5uxwcmvhd6mzthxuvev1sl"
        assert tracking_dataset.records[0].players_coordinates[
            away_player
        ] == Point(x=30.595, y=44.022)
        assert away_player.position == "Defender"
        assert away_player.jersey_no == 2
        assert away_player.starting
        assert away_player.team == away_team

        away_substitute = away_team.players[15]
        assert away_substitute.jersey_no == 18
        assert away_substitute.position == "Substitute"
        assert not away_substitute.starting
        assert away_substitute.team == away_team

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


class TestStatsPerformEvent:
    """Tests related to deserializing the MA3 event data feed.

    See Also:
        kloppy.tests.test_opta.TestOptaEvent
    """

    def test_deserialize_all(self, event_dataset: EventDataset):
        assert event_dataset.metadata.provider == Provider.STATSPERFORM
        assert event_dataset.metadata.coordinate_system == OptaCoordinateSystem(
            # StatsPerform does not provide pitch dimensions
            pitch_length=None,
            pitch_width=None,
        )
        assert len(event_dataset.records) == 1652


class TestStatsPerformTracking:
    """Tests related to deserializing tracking data delivered by StatsPerform."""

    def test_orientation(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_framerate(self, tracking_dataset: TrackingDataset):
        assert tracking_dataset.metadata.frame_rate == 10.0

    def test_flags(self, tracking_dataset):
        assert tracking_dataset.metadata.flags == DatasetFlag.BALL_STATE

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
        assert pitch_dimensions.x_dim.max == None
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == None

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
            x=50.615 / 105, y=1 - 35.325 / 68, z=0.0
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
