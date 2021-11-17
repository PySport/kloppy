import os

import pytest

from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    Point3D,
    DatasetType,
)

from kloppy import skillcorner


class TestSkillCornerTracking:
    @pytest.fixture
    def meta_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/skillcorner_match_data.json"

    @pytest.fixture
    def raw_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/skillcorner_structured_data.json"

    def test_correct_deserialization(self, raw_data: str, meta_data: str):
        dataset = skillcorner.load(
            meta_data=meta_data, raw_data=raw_data, coordinates="skillcorner"
        )

        assert dataset.metadata.provider == Provider.SKILLCORNER
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 34783
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_TEAM
        assert dataset.metadata.periods[1] == Period(
            id=1,
            start_timestamp=0.0,
            end_timestamp=2753.3,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )
        assert dataset.metadata.periods[2] == Period(
            id=2,
            start_timestamp=2700.0,
            end_timestamp=5509.7,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )

        # are frames with wrong camera views and pregame skipped?
        assert dataset.records[0].timestamp == 11.2

        # make sure data is loaded correctly
        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=33.8697315398, y=-9.55742259253)

        away_player = dataset.metadata.teams[1].players[9]
        assert dataset.records[0].players_data[
            away_player
        ].coordinates == Point(x=25.9863082795, y=27.3013598578)

        assert dataset.records[1].ball_coordinates == Point3D(
            x=30.5914728131, y=35.3622277834, z=2.24371228757
        )

        # check that missing ball-z_coordinate is identified as None
        assert dataset.records[38].ball_coordinates == Point3D(
            x=11.6568802848, y=24.7214038909, z=None
        )

        # check that 'ball_z' column is included in to_pandas dataframe
        # frame = _frame_to_pandas_row_converter(dataset.records[38])
        # assert "ball_z" in frame.keys()

        # make sure player data is only in the frame when the player is in view
        assert "home_1" not in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]

        assert "away_1" not in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]

        # are anonymous players loaded correctly?
        home_anon_75 = [
            player
            for player in dataset.records[87].players_data
            if player.player_id == "home_anon_75"
        ]
        assert home_anon_75 == [
            player
            for player in dataset.records[88].players_data
            if player.player_id == "home_anon_75"
        ]

        # is pitch dimension set correctly?
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.5
        assert pitch_dimensions.x_dim.max == 52.5
        assert pitch_dimensions.y_dim.min == -34
        assert pitch_dimensions.y_dim.max == 34

    def test_correct_normalized_deserialization(
        self, meta_data: str, raw_data: str
    ):
        base_dir = os.path.dirname(__file__)
        dataset = skillcorner.load(meta_data=meta_data, raw_data=raw_data)

        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=0.8225688718076191, y=0.6405503322430882)
