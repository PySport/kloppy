from math import sqrt, isnan
import numpy as np

import pytest

from kloppy.domain import (
    Period,
    DatasetFlag,
    Point,
    AttackingDirection,
    TrackingDataset,
    NormalizedPitchDimensions,
    Dimension,
    Orientation,
    Provider,
    Frame,
    Metadata,
    MetricaCoordinateSystem,
    Team,
    Ground,
    Player,
    Detection,
    Point3D,
)


class TestHelpers:
    def _get_tracking_dataset(self):
        home_team = Team(team_id="home", name="home", ground=Ground.HOME)
        home_team.players = [
            Player(team=home_team, player_id=f"home_1", jersey_no=1)
        ]
        away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        away_team.players = [
            Player(team=away_team, player_id=f"away_1", jersey_no=1)
        ]
        teams = [home_team, away_team]

        periods = [
            Period(
                id=1,
                start_timestamp=0.0,
                end_timestamp=10.0,
            ),
        ]
        metadata = Metadata(
            flags=(DatasetFlag.BALL_OWNING_TEAM),
            pitch_dimensions=NormalizedPitchDimensions(
                x_dim=Dimension(0, 100),
                y_dim=Dimension(0, 100),
                pitch_length=105,
                pitch_width=68,
            ),
            orientation=Orientation.HOME_AWAY,
            frame_rate=25,
            periods=periods,
            teams=teams,
            score=None,
            provider=None,
            coordinate_system=None,
        )

        tracking_data = TrackingDataset(
            metadata=metadata,
            records=[
                Frame(
                    frame_id=i,
                    timestamp=i / 25,
                    ball_owning_team=teams[0],
                    ball_state=None,
                    period=periods[0],
                    players_data={
                        Player(
                            team=home_team, player_id="home_1", jersey_no=1
                        ): Detection(
                            coordinates=Point(x=0, y=0),
                        )
                    },
                    other_data={"extra_data": 1},
                    ball_data=Detection(coordinates=Point3D(x=0, y=0, z=0)),
                )
                for i in range(25)  # not moving for one second
            ]
            + [
                Frame(
                    frame_id=25 + i,
                    timestamp=(25 + i) / 25,
                    ball_owning_team=teams[0],
                    ball_state=None,
                    period=periods[0],
                    players_data={
                        Player(
                            team=home_team, player_id="home_1", jersey_no=1
                        ): Detection(
                            coordinates=Point(x=0 + i, y=0 + i),
                        )
                    },
                    other_data={"extra_data": 1},
                    ball_data=Detection(
                        coordinates=Point3D(x=0 + i, y=0 + i, z=0)
                    ),
                )
                for i in range(100)  # 125.096m in 4 seconds
            ],
        )
        return tracking_data

    def test_compute_kinematics(self):
        dataset = self._get_tracking_dataset().compute_kinematics(
            # disable all filters
            n_smooth_speed=1,
            n_smooth_acc=1,
            filter_type=None,
        )

        ball_speeds = [frame.ball_data.speed for frame in dataset.records]
        # The ball speed is not defined for the first frame
        assert isnan(ball_speeds[0])
        # The ball ball does not move for the first 25 frames
        assert ball_speeds[1:25] == pytest.approx([0] * 24)
        # The ball moves with a constant speed in the next 100 frames
        assert ball_speeds[26:] == pytest.approx(
            [sqrt(105**2 + 68**2) / 4] * 99
        )

        ball_accelerations = [
            frame.ball_data.acceleration for frame in dataset.records
        ]
        # The ball acceleration is not defined for the first frame
        assert isnan(ball_accelerations[0])
        # The ball only accelerates at the 26th frame
        assert ball_accelerations[25] == pytest.approx(0)
        assert np.nanargmax(ball_accelerations) == 26
        assert ball_accelerations[27] == pytest.approx(0)

        # It should also compute the speed and acceleration for the players
        for player in dataset.metadata.teams[0].players:
            player_speeds = [
                frame.players_data[player].speed for frame in dataset.records
            ]
            assert player_speeds[26:] == pytest.approx(
                [sqrt(105**2 + 68**2) / 4] * 99
            )
            player_accelerations = [
                frame.players_data[player].acceleration
                for frame in dataset.records
            ]
            assert np.nanargmax(player_accelerations) == 26

    def test_compute_kinematics_with_filter(self):
        dataset = self._get_tracking_dataset()
        dataset.compute_kinematics(
            n_smooth_speed=2, n_smooth_acc=2, filter_type="savitzky_golay"
        )
        dataset.compute_kinematics(
            n_smooth_speed=2, n_smooth_acc=2, filter_type="moving_average"
        )
