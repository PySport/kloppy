import os

from kloppy import TRACABSerializer
from kloppy.domain import (
    Period,
    AttackingDirection,
    Orientation,
    Point,
    BallState,
    Team,
)


class TestTracabTracking:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = TRACABSerializer()

        with open(
            f"{base_dir}/files/tracab_meta.xml", "rb"
        ) as meta_data, open(
            f"{base_dir}/files/tracab_raw.dat", "rb"
        ) as raw_data:

            dataset = serializer.deserialize(
                inputs={"meta_data": meta_data, "raw_data": raw_data},
                options={"only_alive": False},
            )

        assert len(dataset.records) == 6
        assert len(dataset.periods) == 2
        assert dataset.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.periods[0] == Period(
            id=1,
            start_timestamp=4.0,
            end_timestamp=4.08,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )

        assert dataset.periods[1] == Period(
            id=2,
            start_timestamp=8.0,
            end_timestamp=8.08,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        assert dataset.records[0].home_team_player_positions["19"] == Point(
            x=-1234.0, y=-294.0
        )
        assert dataset.records[0].away_team_player_positions["19"] == Point(
            x=8889, y=-666
        )
        assert dataset.records[0].ball_position == Point(x=-27, y=25)
        assert dataset.records[0].ball_state == BallState.ALIVE
        assert dataset.records[0].ball_owning_team == Team.HOME

        assert dataset.records[1].ball_owning_team == Team.AWAY

        assert dataset.records[2].ball_state == BallState.DEAD

        # make sure player data is only in the frame when the player is at the pitch
        assert "1337" not in dataset.records[0].away_team_player_positions
        assert "1337" in dataset.records[3].away_team_player_positions
