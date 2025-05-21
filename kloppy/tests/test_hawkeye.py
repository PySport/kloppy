import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import pytest

from kloppy import hawkeye
from kloppy.domain import (
    DatasetType,
    HawkEyeCoordinateSystem,
    Orientation,
    Point,
    Point3D,
    Provider,
    TrackingDataset,
)


@pytest.fixture(scope="session")
def ball_feeds(base_dir: Path) -> List[Path]:
    return [
        base_dir / "files" / "hawkeye_1_1.football.samples.ball",
        base_dir / "files" / "hawkeye_2_46.football.samples.ball",
    ]


@pytest.fixture(scope="session")
def player_centroid_feeds(base_dir: Path) -> List[Path]:
    return [
        base_dir / "files" / "hawkeye_1_1.football.samples.centroids",
        base_dir / "files" / "hawkeye_2_46.football.samples.centroids",
    ]


@pytest.fixture(scope="session")
def meta_data_xml(base_dir: Path) -> Path:
    return base_dir / "files" / "hawkeye_meta.xml"


@pytest.fixture(scope="session")
def meta_data_json(base_dir: Path) -> Path:
    return base_dir / "files" / "hawkeye_meta.json"


class TestsHawkEyeInputs:
    """Tests related to the various input options."""

    def test_deserialize_single_file(
        self, ball_feeds: List[Path], player_centroid_feeds: List[Path]
    ):
        dataset = hawkeye.load(
            ball_feeds=ball_feeds[0],
            player_centroid_feeds=player_centroid_feeds[0],
            coordinates="hawkeye",
        )
        assert len(dataset) == 3000

    def test_deserialize_multiple_files(
        self,
        ball_feeds: List[Path],
        player_centroid_feeds: List[Path],
    ):
        dataset = hawkeye.load(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            coordinates="hawkeye",
        )
        assert len(dataset) == 6000

    def test_deserialize_directory(self, base_dir: Path):
        dataset = hawkeye.load(
            ball_feeds=(base_dir / "files").resolve(),
            player_centroid_feeds=(base_dir / "files").resolve(),
            coordinates="hawkeye",
        )
        assert len(dataset) == 6000

    def test_limit(
        self, ball_feeds: List[Path], player_centroid_feeds: List[Path]
    ):
        dataset = hawkeye.load(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            coordinates="hawkeye",
            limit=10,
        )
        assert len(dataset) == 10

    def test_sample_rate(
        self, ball_feeds: List[Path], player_centroid_feeds: List[Path]
    ):
        dataset = hawkeye.load(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            coordinates="hawkeye",
            sample_rate=1 / 2,
            limit=300,
        )
        assert len(dataset) == 300
        assert dataset.metadata.frame_rate == 50
        assert dataset.records[0].timestamp.total_seconds() == 0.000080
        assert dataset.records[1].timestamp.total_seconds() == 0.040078

    def test_overwrite_metadata(
        self,
        ball_feeds: List[Path],
        player_centroid_feeds: List[Path],
        meta_data_json: Path,
    ):
        dataset = hawkeye.load(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            pitch_length=120.0,
            pitch_width=70.0,
            coordinates="hawkeye",
        )
        assert dataset.metadata.coordinate_system.pitch_length == 120.0
        assert dataset.metadata.coordinate_system.pitch_width == 70.0

        dataset = hawkeye.load(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            meta_data=meta_data_json,
            pitch_length=120.0,
            pitch_width=70.0,
            coordinates="hawkeye",
        )
        assert dataset.metadata.coordinate_system.pitch_length == 104.0
        assert dataset.metadata.coordinate_system.pitch_width == 67.0


class TestHawkEyeDeserializer:
    """Tests related to checking the correctness of the deserialization."""

    @pytest.fixture(scope="class")
    def dataset(
        self, ball_feeds: List[Path], player_centroid_feeds: List[Path]
    ) -> TrackingDataset:
        dataset = hawkeye.load(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            pitch_length=105.0,
            pitch_width=68.0,
            coordinates="hawkeye",
        )
        assert len(dataset) == 6000
        assert dataset.dataset_type == DatasetType.TRACKING
        return dataset

    def test_provider(self, dataset: TrackingDataset):
        """It should set the provider"""
        assert dataset.metadata.provider == Provider.HAWKEYE

    def test_orientation(self, dataset):
        """It should set the correct orientation"""
        assert dataset.metadata.orientation == Orientation.HOME_AWAY

    def test_frame_rate(self, dataset):
        """It should set the frame rate to 25"""
        assert dataset.metadata.frame_rate == 50

    def test_teams(self, dataset):
        """It should create the teams and player objects"""
        # There should be two teams with the correct names
        assert dataset.metadata.teams[0].name == "Team A"
        assert dataset.metadata.teams[0].starting_formation is None
        assert dataset.metadata.teams[1].name == "Team B"
        assert dataset.metadata.teams[1].starting_formation is None
        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("487487")
        assert player.player_id == "487487"
        assert player.jersey_no == 4
        assert str(player) == "away_4"

    def test_periods(self, dataset):
        """It should create the periods"""
        assert dataset.metadata.periods[0].id == 1
        assert len(dataset.metadata.periods) == 2

        assert dataset.metadata.periods[
            0
        ].start_timestamp == datetime.strptime(
            "2024-09-22T21:00:49.383Z", "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        assert dataset.metadata.periods[0].end_timestamp == datetime.strptime(
            "2024-09-22T21:47:30.592Z", "%Y-%m-%dT%H:%M:%S.%fZ"
        )

        assert dataset.metadata.periods[
            1
        ].start_timestamp == datetime.strptime(
            "2024-09-22T22:03:13.540Z", "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        assert dataset.metadata.periods[1].end_timestamp == datetime.strptime(
            "2024-09-22T23:00:26.296Z", "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        assert isinstance(
            dataset.metadata.coordinate_system, HawkEyeCoordinateSystem
        )

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.5
        assert pitch_dimensions.x_dim.max == 52.5
        assert pitch_dimensions.y_dim.min == -34.0
        assert pitch_dimensions.y_dim.max == 34.0

    def test_timestamps(self, dataset):
        """It should set the correct timestamps"""
        assert math.isclose(
            dataset.records[0].timestamp.total_seconds(),
            timedelta(seconds=8e-05).total_seconds(),
            rel_tol=1e-5,
        )
        assert math.isclose(
            dataset.records[400].timestamp.total_seconds(),
            timedelta(seconds=8.019669).total_seconds(),
            rel_tol=1e-5,
        )
        # second frame second half
        assert math.isclose(
            dataset.records[3001].timestamp.total_seconds(),
            timedelta(seconds=0.02008).total_seconds(),
            rel_tol=1e-5,
        )

    def test_ball_coordinates(self, dataset):
        """It should set the correct ball coordinates"""
        assert dataset.records[1].ball_coordinates == Point3D(
            x=0.2773038337512226, y=-0.06614051219344752, z=0.21062164074548867
        )

    def test_player_coordinates(self, dataset):
        """It should set the correct player coordinates"""
        home_player = dataset.metadata.teams[0].players[3]
        assert home_player.player_id == "487487"
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=21.757139205932617, y=-4.809798240661621
        )

        away_player = dataset.metadata.teams[1].players[3]
        assert away_player.player_id == "487721"
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=-0.41805464029312134, y=-9.460993766784668
        )


def test_xml_metadata(
    ball_feeds: List[Path],
    player_centroid_feeds: List[Path],
    meta_data_xml: Path,
):
    dataset = hawkeye.load(
        ball_feeds=ball_feeds,
        player_centroid_feeds=player_centroid_feeds,
        meta_data=meta_data_xml,
        coordinates="hawkeye",
    )
    # Check pitch dimensions
    pitch_dimensions = dataset.metadata.pitch_dimensions
    assert pitch_dimensions.x_dim.min == -53.0
    assert pitch_dimensions.x_dim.max == 53.0
    assert pitch_dimensions.y_dim.min == -34.5
    assert pitch_dimensions.y_dim.max == 34.5

    # Check enriched metadata
    date = dataset.metadata.date
    if date:
        assert isinstance(date, datetime)
        assert date == datetime(
            2024, 1, 1, 10, 8, 38, 979000, tzinfo=timezone.utc
        )

    game_week = dataset.metadata.game_week
    if game_week:
        assert isinstance(game_week, str)
        assert game_week == "1"

    game_id = dataset.metadata.game_id
    if game_id:
        assert isinstance(game_id, str)
        assert game_id == "288226"


def test_json_metadata(
    ball_feeds: List[Path],
    player_centroid_feeds: List[Path],
    meta_data_json: Path,
):
    dataset = hawkeye.load(
        ball_feeds=ball_feeds,
        player_centroid_feeds=player_centroid_feeds,
        meta_data=meta_data_json,
        coordinates="hawkeye",
    )
    # Check pitch dimensions
    pitch_dimensions = dataset.metadata.pitch_dimensions
    assert pitch_dimensions.x_dim.min == -52
    assert pitch_dimensions.x_dim.max == 52
    assert pitch_dimensions.y_dim.min == -33.5
    assert pitch_dimensions.y_dim.max == 33.5

    # Check enriched metadata
    date = dataset.metadata.date
    if date:
        assert isinstance(date, datetime)
        assert date == datetime(
            2024, 1, 1, 10, 8, 38, 979000, tzinfo=timezone.utc
        )

    game_week = dataset.metadata.game_week
    if game_week:
        assert isinstance(game_week, str)
        assert game_week == "1"

    game_id = dataset.metadata.game_id
    if game_id:
        assert isinstance(game_id, str)
        assert game_id == "288226"


def test_correct_normalized_deserialization(
    ball_feeds: List[Path],
    player_centroid_feeds: List[Path],
):
    dataset = hawkeye.load(
        ball_feeds=ball_feeds,
        player_centroid_feeds=player_centroid_feeds,
    )

    home_player = dataset.metadata.teams[0].players[3]
    assert dataset.records[0].players_coordinates[home_player] == Point(
        x=0.7072108495803107, y=0.5707323270685533
    )
    assert (
        dataset.records[100].players_data[home_player].speed
        == 3.963825734080879
    )

    # Check normalised pitch dimensions
    pitch_dimensions = dataset.metadata.pitch_dimensions
    assert pitch_dimensions.x_dim.min == 0.0
    assert pitch_dimensions.x_dim.max == 1.0
    assert pitch_dimensions.y_dim.min == 0.0
    assert pitch_dimensions.y_dim.max == 1.0
