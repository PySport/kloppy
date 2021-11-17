import os

import pytest

from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    DatasetType,
)

from kloppy import metrica


class TestMetricaCsvTracking:
    """"""

    @pytest.fixture
    def home_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/metrica_home.csv"

    @pytest.fixture
    def away_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/metrica_away.csv"

    def test_correct_deserialization(self, home_data: str, away_data: str):
        dataset = metrica.load_tracking_csv(
            home_data=home_data, away_data=away_data
        )
        assert dataset.metadata.provider == Provider.METRICA
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 6
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=0.04,
            end_timestamp=0.12,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=5800.16,
            end_timestamp=5800.24,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        # make sure data is loaded correctly (including flip y-axis)
        home_player = dataset.metadata.teams[0].players[0]
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=0.00082, y=1 - 0.48238)

        away_player = dataset.metadata.teams[1].players[0]
        assert dataset.records[0].players_data[
            away_player
        ].coordinates == Point(x=0.90509, y=1 - 0.47462)

        assert dataset.records[0].ball_coordinates == Point(
            x=0.45472, y=1 - 0.38709
        )

        # make sure player data is only in the frame when the player is at the pitch
        assert "home_14" not in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "home_14" in [
            player.player_id
            for player in dataset.records[3].players_data.keys()
        ]
