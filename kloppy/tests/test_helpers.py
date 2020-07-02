import os

from pandas import DataFrame
from pandas.testing import assert_frame_equal

from kloppy import (
    to_pandas,
    load_metrica_tracking_data,
    load_tracab_tracking_data,
    transform,
)
from kloppy.domain import (
    Period,
    DatasetFlag,
    Point,
    AttackingDirection,
    TrackingDataset,
    PitchDimensions,
    Dimension,
    Orientation,
    Frame,
    EventDataset,
    PassEvent,
)


class TestHelpers:
    def test_load_metrica_tracking_data(self):
        base_dir = os.path.dirname(__file__)
        dataset = load_metrica_tracking_data(
            f"{base_dir}/files/metrica_home.csv",
            f"{base_dir}/files/metrica_away.csv",
        )
        assert len(dataset.records) == 6
        assert len(dataset.periods) == 2

    def test_load_tracab_tracking_data(self):
        base_dir = os.path.dirname(__file__)
        dataset = load_tracab_tracking_data(
            f"{base_dir}/files/tracab_meta.xml",
            f"{base_dir}/files/tracab_raw.dat",
        )
        assert len(dataset.records) == 5  # only alive=True
        assert len(dataset.periods) == 2

    def _get_tracking_dataset(self):
        periods = [
            Period(
                id=1,
                start_timestamp=0.0,
                end_timestamp=10.0,
                attacking_direction=AttackingDirection.HOME_AWAY,
            ),
            Period(
                id=2,
                start_timestamp=15.0,
                end_timestamp=25.0,
                attacking_direction=AttackingDirection.AWAY_HOME,
            ),
        ]
        tracking_data = TrackingDataset(
            flags=~(DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE),
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 100), y_dim=Dimension(-50, 50)
            ),
            orientation=Orientation.HOME_TEAM,
            frame_rate=25,
            records=[
                Frame(
                    frame_id=1,
                    timestamp=0.1,
                    ball_owning_team=None,
                    ball_state=None,
                    period=periods[0],
                    away_team_player_positions={},
                    home_team_player_positions={},
                    ball_position=Point(x=100, y=-50),
                ),
                Frame(
                    frame_id=2,
                    timestamp=0.2,
                    ball_owning_team=None,
                    ball_state=None,
                    period=periods[0],
                    away_team_player_positions={"1": Point(x=10, y=20)},
                    home_team_player_positions={"1": Point(x=15, y=35)},
                    ball_position=Point(x=0, y=50),
                ),
            ],
            periods=periods,
        )
        return tracking_data

    def test_transform(self):
        tracking_data = self._get_tracking_dataset()

        # orientation change AND dimension scale
        transformed_dataset = transform(
            tracking_data,
            to_orientation="AWAY_TEAM",
            to_pitch_dimensions=[[0, 1], [0, 1]],
        )

        assert transformed_dataset.frames[0].ball_position == Point(x=0, y=1)
        assert transformed_dataset.frames[1].ball_position == Point(x=1, y=0)

    def test_to_pandas(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = to_pandas(tracking_data)

        expected_data_frame = DataFrame.from_dict(
            {
                "period_id": {0: 1, 1: 1},
                "timestamp": {0: 0.1, 1: 0.2},
                "ball_state": {0: None, 1: None},
                "ball_owning_team": {0: None, 1: None},
                "ball_x": {0: 100, 1: 0},
                "ball_y": {0: -50, 1: 50},
                "player_home_1_x": {0: None, 1: 15.0},
                "player_home_1_y": {0: None, 1: 35.0},
                "player_away_1_x": {0: None, 1: 10.0},
                "player_away_1_y": {0: None, 1: 20.0},
            }
        )

        assert_frame_equal(data_frame, expected_data_frame)

    def test_to_pandas_additional_columns(self):
        tracking_data = self._get_tracking_dataset()

        data_frame = to_pandas(
            tracking_data,
            additional_columns={
                "match": "test",
                "bonus_column": lambda frame: frame.frame_id + 10,
            },
        )

        expected_data_frame = DataFrame.from_dict(
            {
                "period_id": [1, 1],
                "timestamp": [0.1, 0.2],
                "ball_state": [None, None],
                "ball_owning_team": [None, None],
                "ball_x": [100, 0],
                "ball_y": [-50, 50],
                "match": ["test", "test"],
                "bonus_column": [11, 12],
                "player_home_1_x": [None, 15],
                "player_home_1_y": [None, 35],
                "player_away_1_x": [None, 10],
                "player_away_1_y": [None, 20],
            }
        )

        assert_frame_equal(data_frame, expected_data_frame)
