from pathlib import Path

import pytest

from kloppy import statsperform
from kloppy.domain import (
    AttackingDirection,
    DatasetType,
    Orientation,
    Point,
    Point3D,
    Provider,
)


@pytest.fixture
def meta_data_xml(base_dir) -> Path:
    return base_dir / "files/statsperform_ma1_metadata.xml"


@pytest.fixture
def meta_data_json(base_dir) -> Path:
    return base_dir / "files/statsperform_ma1_metadata.json"


@pytest.fixture
def raw_data(base_dir) -> Path:
    return base_dir / "files/statsperform_ma25_tracking.txt"


@pytest.mark.parametrize(
    "meta_data",
    [
        pytest.lazy_fixture("meta_data_xml"),
        pytest.lazy_fixture("meta_data_json"),
    ],
)
class TestStatsPerformTracking:
    def test_correct_deserialization(self, meta_data: Path, raw_data: Path):
        dataset = statsperform.load(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="statsperform",
        )

        # Check provider, type, shape, orientation
        assert dataset.metadata.provider == Provider.STATSPERFORM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 92
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.FIXED_AWAY_HOME

        # Check the periods
        assert dataset.metadata.periods[1].id == 1
        assert dataset.metadata.periods[1].start_timestamp == 0
        assert dataset.metadata.periods[1].end_timestamp == 2500
        assert (
            dataset.metadata.periods[1].attacking_direction
            == AttackingDirection.AWAY_HOME
        )

        assert dataset.metadata.periods[2].id == 2
        assert dataset.metadata.periods[2].start_timestamp == 0
        assert dataset.metadata.periods[2].end_timestamp == 6500
        assert (
            dataset.metadata.periods[2].attacking_direction
            == AttackingDirection.HOME_AWAY
        )

        # Check some timestamps
        assert dataset.records[0].timestamp == 0  # First frame
        assert dataset.records[20].timestamp == 2.0  # Later frame

        # Check some players
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

        # Check the ball
        assert dataset.records[1].ball_coordinates == Point3D(
            x=50.615, y=35.325, z=0.0
        )

        # Check pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max == 100
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == 100

    def test_correct_normalized_deserialization(
        self, meta_data: str, raw_data: str
    ):
        dataset = statsperform.load(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
        )

        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=0.6868899999999999, y=0.6025
        )

        # Check normalised pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0.0
        assert pitch_dimensions.x_dim.max == 1.0
        assert pitch_dimensions.y_dim.min == 0.0
        assert pitch_dimensions.y_dim.max == 1.0
