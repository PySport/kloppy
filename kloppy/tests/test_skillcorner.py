from datetime import timedelta
from pathlib import Path

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
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/skillcorner_match_data.json"

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/skillcorner_structured_data.json"

    def test_correct_deserialization(self, raw_data: Path, meta_data: Path):
        dataset = skillcorner.load(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates="skillcorner",
            include_empty_frames=True,
        )

        assert dataset.metadata.provider == Provider.SKILLCORNER
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 55632
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=1411 / 10
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=28944 / 10
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=39979 / 10
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=68076 / 10
        )

        assert dataset.records[0].frame_id == 1411
        assert dataset.records[0].timestamp == timedelta(seconds=0)
        assert dataset.records[27534].frame_id == 39979
        assert dataset.records[27534].timestamp == timedelta(seconds=0)

        # make sure skillcorner ID is used as player ID
        assert dataset.metadata.teams[0].players[0].player_id == "10247"

        # make sure data is loaded correctly
        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[112].players_data[
            home_player
        ].coordinates == Point(x=33.8697315398, y=-9.55742259253)

        away_player = dataset.metadata.teams[1].players[9]
        assert dataset.records[112].players_data[
            away_player
        ].coordinates == Point(x=25.9863082795, y=27.3013598578)

        assert dataset.records[113].ball_coordinates == Point3D(
            x=30.5914728131, y=35.3622277834, z=2.24371228757
        )

        # check that missing ball-z_coordinate is identified as None
        assert dataset.records[150].ball_coordinates == Point3D(
            x=11.6568802848, y=24.7214038909, z=None
        )

        # check that 'ball_z' column is included in to_pandas dataframe
        # frame = _frame_to_pandas_row_converter(dataset.records[150])
        # assert "ball_z" in frame.keys()

        # make sure player data is only in the frame when the player is in view
        assert "home_1" not in [
            player.player_id
            for player in dataset.records[112].players_data.keys()
        ]

        assert "away_1" not in [
            player.player_id
            for player in dataset.records[112].players_data.keys()
        ]

        # are anonymous players loaded correctly?
        home_anon_75 = [
            player
            for player in dataset.records[197].players_data
            if player.player_id == "home_anon_75"
        ]
        assert home_anon_75 == [
            player
            for player in dataset.records[200].players_data
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
        dataset = skillcorner.load(meta_data=meta_data, raw_data=raw_data)

        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=0.8225688718076191, y=0.6405503322430882)

    def test_skip_empty_frames(self, meta_data: str, raw_data: str):
        dataset = skillcorner.load(
            meta_data=meta_data, raw_data=raw_data, include_empty_frames=False
        )

        assert len(dataset.records) == 34783
        assert dataset.records[0].timestamp == timedelta(seconds=11.2)
