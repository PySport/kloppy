import os

import pytest

from kloppy.domain import (
    AttackingDirection,
    Orientation,
    Provider,
    Point,
    Point3D,
    DatasetType,
)

from kloppy import statsperform


class TestStatsperformTracking:
    @pytest.fixture
    def meta_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsperform_2456693_metadata.xml"

    @pytest.fixture
    def raw_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsperform_2456693_tracking.TXT"

    @pytest.fixture
    def player_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsperform_2456693_players.csv"

    def test_correct_deserialization(
        self, meta_data: str, raw_data: str, player_data: str
    ):
        dataset = statsperform.load(
            meta_data=meta_data,
            raw_data=raw_data,
            player_data=player_data,
            only_alive=False,
            coordinates="statsperform",
        )
        df = dataset.to_df()
        a = 3
        # Check provider, type, shape, etc
        assert dataset.metadata.provider == Provider.STATSPERFORM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 241
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.FIXED_AWAY_HOME

        # Check the Periods
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == 0
        assert dataset.metadata.periods[0].end_timestamp == 4500
        assert (
            dataset.metadata.periods[0].attacking_direction
            == AttackingDirection.AWAY_HOME
        )

        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == 0
        assert dataset.metadata.periods[1].end_timestamp == 19400
        assert (
            dataset.metadata.periods[1].attacking_direction
            == AttackingDirection.HOME_AWAY
        )

        # Check some timestamps
        assert dataset.records[0].timestamp == 0  # First frame
        assert dataset.records[20].timestamp == 2.0  # Later frame

        # Check some players
        home_player = dataset.metadata.teams[0].players[2]
        assert home_player.player_id == 563011
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=68.602, y=18.053
        )

        away_player = dataset.metadata.teams[1].players[3]
        assert away_player.player_id == 733878
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=43.902, y=29.934
        )

        # Check the ball
        assert dataset.records[1].ball_coordinates == Point3D(
            x=53.71, y=33.39, z=0.0
        )

        # Check pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max == 100
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == 100

    def test_correct_normalized_deserialization(
        self, meta_data: str, raw_data: str, player_data: str
    ):
        dataset = statsperform.load(
            meta_data=meta_data,
            raw_data=raw_data,
            player_data=player_data,
        )

        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=0.6860200000000001, y=0.81947
        )

        # Check normalised pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0.0
        assert pitch_dimensions.x_dim.max == 1.0
        assert pitch_dimensions.y_dim.min == 0.0
        assert pitch_dimensions.y_dim.max == 1.0
