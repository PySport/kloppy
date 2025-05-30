from datetime import timedelta
from typing import IO, Iterator, List, Tuple

from kloppy.domain import (
    BallState,
    Frame,
    Period,
    Player,
    PlayerData,
    Point,
    Point3D,
    Team,
)
from kloppy.domain.services.frame_factory import create_frame
from kloppy.exceptions import DeserializationError

from .base import TracabDataParser


class TracabDatParser(TracabDataParser):
    def __init__(
        self,
        feed: IO[bytes],
        periods: List[Period],
        teams: Tuple[Team, Team],
        frame_rate: int,
    ) -> None:
        self.root = feed.readlines()
        self.periods = periods
        self.teams = teams
        self.frame_rate = frame_rate

    def extract_frames(
        self, sample_rate: float, only_alive: bool
    ) -> Iterator[Frame]:
        n = 0
        sample = 1.0 / sample_rate

        for line in self.root:
            line = line.strip().decode("ascii")
            if not line:
                continue

            frame_id = int(line[:10].split(":", 1)[0])
            if only_alive and not line.endswith("Alive;:"):
                continue

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
                        frame = self._parse_frame(period, line)
                        yield frame
                    n += 1

    def _parse_frame(self, period, line) -> Frame:
        line = str(line)
        frame_id, players, ball = line.strip().split(":")[:3]

        players_data = {}

        for player_data in players.split(";")[:-1]:
            team_id, target_id, jersey_no, x, y, speed = player_data.split(",")
            team_id = int(team_id)

            if team_id == 1:
                team = self.teams[0]
            elif team_id == 0:
                team = self.teams[1]
            elif team_id in (-1, 3, 4):
                continue
            else:
                raise DeserializationError(
                    f"Unknown Player Team ID: {team_id}"
                )

            player = team.get_player_by_jersey_number(jersey_no)

            if not player:
                player = Player(
                    player_id=f"{team.ground}_{jersey_no}",
                    team=team,
                    jersey_no=int(jersey_no),
                )
                team.players.append(player)

            players_data[player] = PlayerData(
                coordinates=Point(float(x), float(y)), speed=float(speed)
            )

        (
            ball_x,
            ball_y,
            ball_z,
            ball_speed,
            ball_owning_team,
            ball_state,
        ) = ball.rstrip(";").split(",")[:6]

        frame_id = int(frame_id)

        if ball_owning_team == "H":
            ball_owning_team = self.teams[0]
        elif ball_owning_team == "A":
            ball_owning_team = self.teams[1]
        else:
            raise DeserializationError(
                f"Unknown ball owning team: {ball_owning_team}"
            )

        if ball_state == "Alive":
            ball_state = BallState.ALIVE
        elif ball_state == "Dead":
            ball_state = BallState.DEAD
        else:
            raise DeserializationError(f"Unknown ball state: {ball_state}")

        frame = create_frame(
            frame_id=frame_id,
            timestamp=timedelta(seconds=frame_id / self.frame_rate)
            - period.start_timestamp,
            ball_coordinates=Point3D(
                float(ball_x), float(ball_y), float(ball_z)
            ),
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            players_data=players_data,
            period=period,
            other_data={},
        )

        return frame
