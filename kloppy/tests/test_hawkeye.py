from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy.domain import (
    Orientation,
    Provider,
    Point,
    Point3D,
    DatasetType,
    HawkEyeCoordinateSystem,
)

import math

from kloppy import hawkeye


class TestHawkeyeTracking:
    @pytest.fixture
    def meta_data_xml(self, base_dir) -> Path:
        return base_dir / "files" / "hawkeye_meta.xml"

    @pytest.fixture
    def meta_data_json(self, base_dir) -> Path:
        return base_dir / "files" / "hawkeye_meta.json"

    @pytest.fixture
    def ball_feed_file(self, base_dir) -> Path:
        return base_dir / "files" / "hawkeye_1_1.football.samples.ball"

    @pytest.fixture
    def player_feed_file(self, base_dir) -> Path:
        return base_dir / "files" / "hawkeye_1_1.football.samples.centroids"

    @pytest.fixture
    def ball_feed_file_2(self, base_dir) -> Path:
        return base_dir / "files" / "hawkeye_2_46.football.samples.ball"

    @pytest.fixture
    def player_feed_file_2(self, base_dir) -> Path:
        return base_dir / "files" / "hawkeye_2_46.football.samples.centroids"

    def test_single_file_deserialization(
        self, ball_feed_file: Path, player_feed_file: Path
    ):
        dataset = hawkeye.load(
            ball_feeds=ball_feed_file,
            player_centroid_feeds=player_feed_file,
            coordinates="hawkeye",
        )
        assert len(dataset) == 3000
        assert dataset.metadata.provider == Provider.HAWKEYE
        assert dataset.dataset_type == DatasetType.TRACKING

    def test_folder_deserialization(self, base_dir: str):
        dataset = hawkeye.load(
            ball_feeds=base_dir / "files",
            player_centroid_feeds=base_dir / "files",
            coordinates="hawkeye",
        )
        assert len(dataset) == 6000
        assert dataset.metadata.provider == Provider.HAWKEYE
        assert dataset.dataset_type == DatasetType.TRACKING

    def test_file_list_deserialization(
        self,
        ball_feed_file: Path,
        player_feed_file: Path,
        ball_feed_file_2: Path,
        player_feed_file_2: Path,
    ):
        dataset = hawkeye.load(
            ball_feeds=[ball_feed_file, ball_feed_file_2],
            player_centroid_feeds=[player_feed_file, player_feed_file_2],
            coordinates="hawkeye",
        )
        assert len(dataset) == 6000
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert len(dataset.metadata.periods) == 2
        assert isinstance(
            dataset.metadata.coordinate_system, HawkEyeCoordinateSystem
        )

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

        # Check some players
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

        # Check the ball
        assert dataset.records[1].ball_coordinates == Point3D(
            x=0.2773038337512226, y=-0.06614051219344752, z=0.21062164074548867
        )

        # Check pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.5
        assert pitch_dimensions.x_dim.max == 52.5
        assert pitch_dimensions.y_dim.min == -34.0
        assert pitch_dimensions.y_dim.max == 34.0

    def test_file_list_xml_deserialization(
        self, ball_feed_file: Path, player_feed_file: Path, meta_data_xml: str
    ):
        dataset = hawkeye.load(
            ball_feeds=[ball_feed_file],
            player_centroid_feeds=[player_feed_file],
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

    def test_file_list_json_deserialization(
        self, ball_feed_file: Path, player_feed_file: Path, meta_data_json: str
    ):
        dataset = hawkeye.load(
            ball_feeds=[ball_feed_file],
            player_centroid_feeds=[player_feed_file],
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
        self,
        ball_feed_file: Path,
        player_feed_file: Path,
        ball_feed_file_2: Path,
        player_feed_file_2: Path,
    ):
        dataset = hawkeye.load(
            ball_feeds=[ball_feed_file, ball_feed_file_2],
            player_centroid_feeds=[player_feed_file, player_feed_file_2],
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
