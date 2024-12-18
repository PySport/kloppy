from math import isnan, sqrt

import numpy as np
import pytest

from kloppy.domain import (
    DatasetFlag,
    Detection,
    Dimension,
    Frame,
    Ground,
    Metadata,
    NormalizedPitchDimensions,
    Orientation,
    Period,
    Player,
    Point,
    Point3D,
    Team,
    TrackingDataset,
)


class TestTrackingDataset:
    def _get_tracking_dataset(self):
        """Create a dummy tracking dataset.

        The dataset contains a single player moving in a straight line with
        the ball on their feet. During the first second (or 25 frames), the
        player does not move. During the next four seconds (or 100 frames),
        the player moves at a constant speed.

        No player was detected in frame 10.
        """
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
                    objects={
                        "ball": Detection(
                            coordinates=Point3D(x=0, y=0, z=0),
                        ),
                        home_team.players[0]: Detection(
                            coordinates=Point(x=0, y=0),
                        ),
                    },
                    other_data={"extra_data": 1},
                )
                for i in range(10)  # not moving for one second
            ]
            + [
                Frame(
                    frame_id=10,
                    timestamp=10 / 25,
                    ball_owning_team=teams[0],
                    ball_state=None,
                    period=periods[0],
                    objects={
                        "ball": Detection(
                            coordinates=Point3D(x=0, y=0, z=0),
                        )
                    },
                    other_data={"extra_data": 1},
                )
            ]
            + [
                Frame(
                    frame_id=i,
                    timestamp=i / 25,
                    ball_owning_team=teams[0],
                    ball_state=None,
                    period=periods[0],
                    objects={
                        "ball": Detection(
                            coordinates=Point3D(x=0, y=0, z=0),
                        ),
                        home_team.players[0]: Detection(
                            coordinates=Point(x=0, y=0),
                        ),
                    },
                    other_data={"extra_data": 1},
                )
                for i in range(14)  # not moving for one second
            ]
            + [
                Frame(
                    frame_id=25 + i,
                    timestamp=(25 + i) / 25,
                    ball_owning_team=teams[0],
                    ball_state=None,
                    period=periods[0],
                    objects={
                        "ball": Detection(
                            coordinates=Point3D(x=0 + i, y=0 + i, z=0)
                        ),
                        home_team.players[0]: Detection(
                            coordinates=Point(x=0 + i, y=0 + i),
                        ),
                    },
                    other_data={"extra_data": 1},
                )
                for i in range(100)  # 125.096m in 4 seconds
            ],
        )
        return tracking_data

    def test_ball_data(self):
        dataset = self._get_tracking_dataset()
        frame = dataset[0]
        assert frame.ball_data == Detection(
            coordinates=Point3D(x=0, y=0, z=0),
        )
        assert frame.ball_coordinates == Point3D(x=0, y=0, z=0)
        assert frame.ball_speed is None

    def test_players_data(self):
        dataset = self._get_tracking_dataset()
        frame = dataset[0]
        assert frame.players_data == {
            dataset.metadata.teams[0].players[0]: Detection(
                coordinates=Point(x=0, y=0),
            )
        }
        assert frame.players_coordinates == {
            dataset.metadata.teams[0].players[0]: Point(x=0, y=0),
        }

    def test_getitem(self):
        dataset = self._get_tracking_dataset()
        frame = dataset[0]

        assert frame["ball"] == Detection(
            coordinates=Point3D(x=0, y=0, z=0),
        )
        assert frame["home_1"] == Detection(
            coordinates=Point(x=0, y=0),
        )
        assert frame[dataset.metadata.teams[0].players[0]] == Detection(
            coordinates=Point(x=0, y=0),
        )
        assert frame["home_2"] is None

    def test_trajectories(self):
        dataset = self._get_tracking_dataset()

        ball_trajectories = dataset.trajectories("ball")
        assert len(ball_trajectories) == 1
        assert ball_trajectories[0].start_frame.frame_id == 0
        assert ball_trajectories[0].end_frame.frame_id == 124
        assert len(ball_trajectories[0].detections) == 125
        assert ball_trajectories[0].detections[0] == Detection(
            coordinates=Point3D(x=0, y=0, z=0)
        )

        player_trajectories = dataset.trajectories("home_1")
        assert len(player_trajectories) == 2
        assert player_trajectories[0].start_frame.frame_id == 0
        assert player_trajectories[0].end_frame.frame_id == 9
        assert len(player_trajectories[0].detections) == 10
        assert player_trajectories[0].detections[0] == Detection(
            coordinates=Point(x=0, y=0)
        )
