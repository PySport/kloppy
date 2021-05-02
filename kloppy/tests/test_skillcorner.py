import os

from kloppy import SkillCornerTrackingSerializer
from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    EventType,
    SetPieceType,
)
from kloppy.domain.models.common import DatasetType


class TestSkillCornerTracking:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = SkillCornerTrackingSerializer()

        with open(
            f"{base_dir}/files/skillcorner_structured_data.json", "rb"
        ) as raw_data, open(
            f"{base_dir}/files/skillcorner_match_data.json", "rb"
        ) as metadata:
            dataset = serializer.deserialize(
                inputs={
                    "raw_data": raw_data,
                    "metadata": metadata,
                }
            )
        assert dataset.metadata.provider == Provider.SKILLCORNER
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 34783
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == None
        assert dataset.metadata.periods[1] == Period(
            id=1,
            start_timestamp="0:00.00",
            end_timestamp="45:53.30",
            attacking_direction=AttackingDirection.AWAY_HOME,
        )
        assert dataset.metadata.periods[2] == Period(
            id=2,
            start_timestamp="45:00.00",
            end_timestamp="91:49.70",
            attacking_direction=AttackingDirection.HOME_AWAY,
        )

        # is pregame info skipped?
        assert dataset.records[0].timestamp == "0:11.20"

        # make sure data is loaded correctly (including flip y-axis)
        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=33.8697315398, y=-9.55742259253
        )

        away_player = dataset.metadata.teams[1].players[9]
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=25.9863082795, y=27.3013598578
        )

        assert dataset.records[1].ball_coordinates == Point(
            x=30.5914728131, y=35.3622277834
        )

        # make sure player data is only in the frame when the player is at the pitch
        assert "home_1" not in [
            player.player_id
            for player in dataset.records[0].players_coordinates.keys()
        ]

        assert "away_1" not in [
            player.player_id
            for player in dataset.records[0].players_coordinates.keys()
        ]

        # are anonymous players loaded correctly?
        home_anon_75 = [
            player
            for player in dataset.records[87].players_coordinates
            if player.player_id == "home_anon_75"
        ]
        assert home_anon_75 == [
            player
            for player in dataset.records[88].players_coordinates
            if player.player_id == "home_anon_75"
        ]

        # is pitch dimension set correctly?
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.5
        assert pitch_dimensions.x_dim.max == 52.5
        assert pitch_dimensions.y_dim.min == -34
        assert pitch_dimensions.y_dim.max == 34
