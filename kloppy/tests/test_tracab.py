import os

import pytest

from kloppy.domain import (
    Period,
    AttackingDirection,
    Orientation,
    Provider,
    Point,
    Point3D,
    BallState,
    Team,
    Ground,
    DatasetType,
)

from kloppy import tracab


class TestTracabTracking:
    @pytest.fixture
    def meta_data(self) -> str:
        base_dir = os.path.dirname(__file__)

        return f"{base_dir}/files/tracab_meta.xml"

    @pytest.fixture
    def raw_data(self) -> str:
        base_dir = os.path.dirname(__file__)

        return f"{base_dir}/files/tracab_raw.dat"

    def test_correct_deserialization(self, meta_data: str, raw_data: str):
        dataset = tracab.load(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates="tracab",
            only_alive=False,
        )

        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 6
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=4.0,
            end_timestamp=4.08,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )

        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=8.0,
            end_timestamp=8.08,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        player_home_19 = dataset.metadata.teams[0].get_player_by_jersey_number(
            19
        )
        assert dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=-1234.0, y=-294.0)

        player_away_19 = dataset.metadata.teams[1].get_player_by_jersey_number(
            19
        )
        assert dataset.records[0].players_data[
            player_away_19
        ].coordinates == Point(x=8889, y=-666)
        assert dataset.records[0].ball_coordinates == Point3D(x=-27, y=25, z=0)
        assert dataset.records[0].ball_state == BallState.ALIVE
        assert dataset.records[0].ball_owning_team == Team(
            team_id="home", name="home", ground=Ground.HOME
        )

        assert dataset.records[1].ball_owning_team == Team(
            team_id="away", name="away", ground=Ground.AWAY
        )

        assert dataset.records[2].ball_state == BallState.DEAD

        # make sure player data is only in the frame when the player is at the pitch
        assert "away_1337" not in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "away_1337" in [
            player.player_id
            for player in dataset.records[3].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, meta_data: str, raw_data: str
    ):
        dataset = tracab.load(
            meta_data=meta_data, raw_data=raw_data, only_alive=False
        )

        player_home_19 = dataset.metadata.teams[0].get_player_by_jersey_number(
            19
        )

        assert dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=0.3766, y=0.5489999999999999)
