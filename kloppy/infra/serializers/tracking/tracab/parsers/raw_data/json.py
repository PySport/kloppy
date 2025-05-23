import json
from datetime import timedelta
from typing import IO, Iterator, List, Tuple

from kloppy.domain import (
    BallState,
    Frame,
    Period,
    PlayerData,
    Point,
    Point3D,
    Team,
)
from kloppy.domain.services.frame_factory import create_frame
from kloppy.exceptions import DeserializationError

from .base import TracabDataParser


class TracabJSONParser(TracabDataParser):
    def __init__(
        self,
        feed: IO[bytes],
        periods: List[Period],
        teams: Tuple[Team, Team],
        frame_rate: int,
    ) -> None:
        self.root = json.load(feed)
        self.periods = periods
        self.teams = teams
        self.frame_rate = frame_rate

    def extract_frames(
        self, sample_rate: float, only_alive: bool
    ) -> Iterator[Frame]:
        raw_data = self.root["FrameData"]

        n = 0
        sample = 1.0 / sample_rate

        for frame in raw_data:
            if only_alive and frame["BallPosition"][0]["BallStatus"] == "Dead":
                continue

            frame_id = frame["FrameCount"]
            for period in self.periods:
                assert isinstance(
                    period.start_timestamp, timedelta
                ), "The period's start_timestamp should be a relative time (i.e., a timedelta object)"
                assert isinstance(
                    period.end_timestamp, timedelta
                ), "The period's start_timestamp should be a relative time (i.e., a timedelta object)"

                if (
                    period.start_timestamp
                    <= timedelta(seconds=frame_id / self.frame_rate)
                    <= period.end_timestamp
                ):
                    if n % sample == 0:
                        frame = self._parse_frame(period, frame)
                        yield frame
                    n += 1

    def _parse_frame(self, period, raw_frame):
        frame_id = raw_frame["FrameCount"]
        raw_players_data = raw_frame["PlayerPositions"]
        raw_ball_position = raw_frame["BallPosition"][0]

        players_data = {}
        for player_data in raw_players_data:
            if player_data["Team"] == 1:
                team = self.teams[0]
            elif player_data["Team"] == 0:
                team = self.teams[1]
            elif player_data["Team"] in (-1, 3, 4):
                continue
            else:
                raise DeserializationError(
                    f"Unknown Player Team ID: {player_data['Team']}"
                )

            jersey_no = player_data["JerseyNumber"]
            x = player_data["X"]
            y = player_data["Y"]
            speed = player_data["Speed"]

            player = team.get_player_by_jersey_number(jersey_no)
            if player:
                players_data[player] = PlayerData(
                    coordinates=Point(x, y), speed=speed
                )
            else:
                # continue
                raise DeserializationError(
                    f"Player not found for player jersey no {jersey_no} of team: {team.name}"
                )

        ball_x = raw_ball_position["X"]
        ball_y = raw_ball_position["Y"]
        ball_z = raw_ball_position["Z"]
        ball_speed = raw_ball_position["Speed"]
        if raw_ball_position["BallOwningTeam"] == "H":
            ball_owning_team = self.teams[0]
        elif raw_ball_position["BallOwningTeam"] == "A":
            ball_owning_team = self.teams[1]
        else:
            raise DeserializationError(
                f"Unknown ball owning team: {raw_ball_position['BallOwningTeam']}"
            )
        if raw_ball_position["BallStatus"] == "Alive":
            ball_state = BallState.ALIVE
        elif raw_ball_position["BallStatus"] == "Dead":
            ball_state = BallState.DEAD
        else:
            raise DeserializationError(
                f"Unknown ball state: {raw_ball_position['BallStatus']}"
            )

        frame = create_frame(
            frame_id=frame_id,
            timestamp=timedelta(seconds=frame_id / self.frame_rate)
            - period.start_timestamp,
            ball_coordinates=Point3D(ball_x, ball_y, ball_z),
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            ball_speed=ball_speed,
            players_data=players_data,
            period=period,
            other_data={},
        )

        return frame
