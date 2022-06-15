import logging
from typing import Tuple, Dict, NamedTuple, IO, Optional, Union

from lxml import objectify

from kloppy.domain import (
    TrackingDataset,
    DatasetFlag,
    AttackingDirection,
    Frame,
    Point,
    Point3D,
    Team,
    BallState,
    Period,
    Orientation,
    attacking_direction_from_frame,
    Metadata,
    Ground,
    Player,
    Provider,
    PlayerData,
)
from kloppy.exceptions import DeserializationError

from kloppy.utils import Readable, performance_logging

from .deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class TRACABInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class TRACABDeserializer(TrackingDataDeserializer[TRACABInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    @property
    def provider(self) -> Provider:
        return Provider.TRACAB

    @classmethod
    def _frame_from_line(cls, teams, period, line, frame_rate):
        line = str(line)
        frame_id, players, ball = line.strip().split(":")[:3]

        players_data = {}

        for player_data in players.split(";")[:-1]:
            team_id, target_id, jersey_no, x, y, speed = player_data.split(",")
            team_id = int(team_id)

            if team_id == 1:
                team = teams[0]
            elif team_id == 0:
                team = teams[1]
            else:
                # it's probably -1, but make sure it doesn't crash
                continue

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
            ball_owning_team = teams[0]
        elif ball_owning_team == "A":
            ball_owning_team = teams[1]
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

        return Frame(
            frame_id=frame_id,
            timestamp=frame_id / frame_rate - period.start_timestamp,
            ball_coordinates=Point3D(
                float(ball_x), float(ball_y), float(ball_z)
            ),
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            players_data=players_data,
            period=period,
            other_data={},
        )

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "metadata" not in inputs:
            raise ValueError("Please specify a value for 'metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    def deserialize(self, inputs: TRACABInputs) -> TrackingDataset:
        # TODO: also used in Metrica, extract to a method
        home_team = Team(team_id="home", name="home", ground=Ground.HOME)
        away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        teams = [home_team, away_team]

        with performance_logging("Loading metadata", logger=logger):
            match = objectify.fromstring(inputs.meta_data.read()).match
            frame_rate = int(match.attrib["iFrameRateFps"])
            pitch_size_width = float(match.attrib["fPitchXSizeMeters"])
            pitch_size_height = float(match.attrib["fPitchYSizeMeters"])

            periods = []
            for period in match.iterchildren(tag="period"):
                start_frame_id = int(period.attrib["iStartFrame"])
                end_frame_id = int(period.attrib["iEndFrame"])
                if start_frame_id != 0 or end_frame_id != 0:
                    periods.append(
                        Period(
                            id=int(period.attrib["iId"]),
                            start_timestamp=start_frame_id / frame_rate,
                            end_timestamp=end_frame_id / frame_rate,
                        )
                    )

        with performance_logging("Loading data", logger=logger):

            transformer = self.get_transformer(
                length=pitch_size_width, width=pitch_size_height
            )

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line_ in inputs.raw_data.readlines():
                    line_ = line_.strip().decode("ascii")
                    if not line_:
                        continue

                    frame_id = int(line_[:10].split(":", 1)[0])
                    if self.only_alive and not line_.endswith("Alive;:"):
                        continue

                    for period_ in periods:
                        if period_.contains(frame_id / frame_rate):
                            if n % sample == 0:
                                yield period_, line_
                            n += 1

            frames = []
            for n, (period, line) in enumerate(_iter()):
                frame = self._frame_from_line(teams, period, line, frame_rate)

                frame = transformer.transform_frame(frame)

                frames.append(frame)

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(
                            frame
                        )
                    )

                if self.limit and n >= self.limit:
                    break

        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY
            else Orientation.FIXED_AWAY_HOME
        )

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=None,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.TRACAB,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
