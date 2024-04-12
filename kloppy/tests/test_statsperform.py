from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kloppy import statsperform
from kloppy.domain import (
    Orientation,
    Point,
    Point3D,
    Provider,
    TrackingDataset,
    DatasetFlag,
    SportVUCoordinateSystem,
)


@pytest.fixture(scope="module")
def meta_data_xml(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_ma1_metadata.xml"


@pytest.fixture(scope="module")
def meta_data_json(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_ma1_metadata.json"


@pytest.fixture(scope="module")
def raw_data(base_dir: Path) -> Path:
    return base_dir / "files" / "statsperform_ma25_tracking.txt"


@pytest.fixture(scope="module", params=["xml", "json"])
def dataset(
    request: pytest.FixtureRequest,
    raw_data: Path,
    meta_data_xml: Path,
    meta_data_json: Path,
) -> TrackingDataset:
    return statsperform.load(
        meta_data=meta_data_xml if request.param == "xml" else meta_data_json,
        raw_data=raw_data,
        only_alive=False,
        provider_name="sportvu",
        coordinates="sportvu",
    )


class TestStatsPerformTracking:
    """Tests related to deserializing tracking data delivered by StatsPerform."""

    def test_provider(self, dataset: TrackingDataset):
        assert dataset.metadata.provider == Provider.STATSPERFORM

    def test_orientation(self, dataset: TrackingDataset):
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_framerate(self, dataset: TrackingDataset):
        assert dataset.metadata.frame_rate == 10.0

    def test_teams(self, dataset: TrackingDataset):
        home_team = dataset.metadata.teams[0]
        home_player = home_team.players[2]
        assert home_player.player_id == "5g5wwp5luxo1rz1kp6chvz0x6"
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=68.689, y=39.75
        )
        assert home_player.position == "Defender"
        assert home_player.jersey_no == 32
        assert home_player.starting
        assert home_player.team == home_team

        away_team = dataset.metadata.teams[1]
        away_player = away_team.players[3]
        assert away_player.player_id == "72d5uxwcmvhd6mzthxuvev1sl"
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=30.595, y=44.022
        )
        assert away_player.position == "Defender"
        assert away_player.jersey_no == 2
        assert away_player.starting
        assert away_player.team == away_team

        away_substitute = away_team.players[15]
        assert away_substitute.jersey_no == 18
        assert away_substitute.position == "Substitute"
        assert not away_substitute.starting
        assert away_substitute.team == away_team

    def test_periods(self, dataset: TrackingDataset):
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == datetime(
            2020, 8, 23, 11, 0, 10
        )
        assert dataset.metadata.periods[0].end_timestamp == datetime(
            2020, 8, 23, 11, 48, 15
        )

        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == datetime(
            2020, 8, 23, 12, 6, 22
        )
        assert dataset.metadata.periods[1].end_timestamp == datetime(
            2020, 8, 23, 12, 56, 30
        )

    def test_flags(self, dataset):
        assert dataset.metadata.flags == DatasetFlag.BALL_STATE

    def test_coordinate_system_without_pitch_dimensions(
        self, raw_data: Path, meta_data_xml: Path
    ):
        dataset = statsperform.load(
            meta_data=meta_data_xml,
            raw_data=raw_data,
            provider_name="sportvu",
            coordinates="sportvu",
        )
        coordinate_system = dataset.metadata.coordinate_system
        pitch_dimensions = dataset.metadata.pitch_dimensions
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
        self, raw_data: Path, meta_data_xml: Path
    ):
        dataset = statsperform.load(
            meta_data=meta_data_xml,
            raw_data=raw_data,
            provider_name="sportvu",
            coordinates="sportvu",
            pitch_length=105,
            pitch_width=68,
        )
        coordinate_system = dataset.metadata.coordinate_system
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert coordinate_system == SportVUCoordinateSystem(
            # StatsPerform does not provide pitch dimensions
            pitch_length=105,
            pitch_width=68,
        )
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max == 105
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == 68

    def test_deserialize_all(self, dataset: TrackingDataset):
        assert len(dataset.records) == 92

    def test_deserialize_only_alive(self, raw_data: Path, meta_data_xml: Path):
        dataset = statsperform.load(
            provider_name="sportvu",
            meta_data=meta_data_xml,
            raw_data=raw_data,
            only_alive=True,
            coordinates="sportvu",
        )
        assert len(dataset.records) == 91

    def test_timestamps(self, dataset: TrackingDataset):
        assert dataset.records[0].timestamp == timedelta(
            seconds=0
        )  # First frame
        assert dataset.records[20].timestamp == timedelta(
            seconds=2.0
        )  # Later frame
        assert dataset.records[26].timestamp == timedelta(
            seconds=0
        )  # Second period

    def test_ball_coordinates(self, dataset: TrackingDataset):
        assert dataset.records[1].ball_coordinates == Point3D(
            x=50.615, y=35.325, z=0.0
        )

    def test_player_coordinates(self, dataset: TrackingDataset):
        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=68.689, y=39.750
        )

    def test_correct_normalized_deserialization(
        self, raw_data: Path, meta_data_xml: Path
    ):
        dataset = statsperform.load(
            provider_name="sportvu",
            pitch_length=105,
            pitch_width=68,
            meta_data=meta_data_xml,
            raw_data=raw_data,
            only_alive=False,
            coordinates="kloppy",
        )

        assert dataset.records[1].ball_coordinates == Point3D(
            x=50.615 / 105, y=1 - 35.325 / 68, z=0.0
        )

        # Check normalised pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0.0
        assert pitch_dimensions.x_dim.max == 1.0
        assert pitch_dimensions.y_dim.min == 0.0
        assert pitch_dimensions.y_dim.max == 1.0

        # Pitch dimensions are required to transform coordinates
        with pytest.raises(ValueError):
            statsperform.load(
                provider_name="sportvu",
                meta_data=meta_data_xml,
                raw_data=raw_data,
                coordinates="kloppy",
            )
