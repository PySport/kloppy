import logging
from datetime import datetime, timedelta, timezone
import warnings
from typing import Dict, Optional, Union
import html

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
    PositionType,
)
from kloppy.exceptions import DeserializationError

from kloppy.utils import Readable, performance_logging

from .common import TRACABInputs, position_types_mapping
from ..deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class TRACABDatDeserializer(TrackingDataDeserializer[TRACABInputs]):
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
            timestamp=timedelta(seconds=frame_id / frame_rate)
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

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "metadata" not in inputs:
            raise ValueError("Please specify a value for 'metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    @staticmethod
    def create_team(
        team_data, ground, start_frame_id, id_suffix="Id", player_item="Player"
    ):
        team = Team(
            team_id=str(team_data[f"Team{id_suffix}"]),
            name=html.unescape(team_data["ShortName"]),
            ground=ground,
        )

        team.players = [
            Player(
                player_id=str(player[f"Player{id_suffix}"]),
                team=team,
                first_name=html.unescape(player["FirstName"]),
                last_name=html.unescape(player["LastName"]),
                name=html.unescape(
                    player["FirstName"] + " " + player["LastName"]
                ),
                jersey_no=int(player["JerseyNo"]),
                starting=player["StartFrameCount"] == start_frame_id,
                starting_position=position_types_mapping.get(
                    player.get("StartingPosition"), PositionType.Unknown
                ),
            )
            for player in team_data["Players"][player_item]
        ]

        return team

    def deserialize(self, inputs: TRACABInputs) -> TrackingDataset:
        with performance_logging("Loading metadata", logger=logger):
            meta_data = objectify.fromstring(inputs.meta_data.read())

            periods = []
            orientation = None

            if hasattr(meta_data, "match"):
                id_suffix = "Id"
                player_item = "Player"

                match = meta_data.match
                frame_rate = int(match.attrib["iFrameRateFps"])
                pitch_size_width = float(
                    match.attrib["fPitchXSizeMeters"].replace(",", ".")
                )
                pitch_size_height = float(
                    match.attrib["fPitchYSizeMeters"].replace(",", ".")
                )
                date = datetime.strptime(
                    meta_data.match.attrib["dtDate"], "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                game_id = meta_data.match.attrib["iId"]

                for period in match.iterchildren(tag="period"):
                    start_frame_id = int(period.attrib["iStartFrame"])
                    end_frame_id = int(period.attrib["iEndFrame"])
                    if start_frame_id != 0 or end_frame_id != 0:
                        periods.append(
                            Period(
                                id=int(period.attrib["iId"]),
                                start_timestamp=timedelta(
                                    seconds=start_frame_id / frame_rate
                                ),
                                end_timestamp=timedelta(
                                    seconds=end_frame_id / frame_rate
                                ),
                            )
                        )
            elif hasattr(meta_data, "Phase1StartFrame"):
                date = datetime.strptime(
                    str(meta_data["Kickoff"]), "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                game_id = str(meta_data["GameID"])
                id_suffix = "ID"
                player_item = "item"

                frame_rate = int(meta_data["FrameRate"])
                pitch_size_width = float(meta_data["PitchLongSide"]) / 100
                pitch_size_height = float(meta_data["PitchShortSide"]) / 100
                for i in [1, 2, 3, 4, 5]:
                    start_frame_id = int(meta_data[f"Phase{i}StartFrame"])
                    end_frame_id = int(meta_data[f"Phase{i}EndFrame"])
                    if start_frame_id != 0 or end_frame_id != 0:
                        periods.append(
                            Period(
                                id=i,
                                start_timestamp=timedelta(
                                    seconds=start_frame_id / frame_rate
                                ),
                                end_timestamp=timedelta(
                                    seconds=end_frame_id / frame_rate
                                ),
                            )
                        )

                orientation = (
                    Orientation.HOME_AWAY
                    if bool(meta_data["Phase1HomeGKLeft"])
                    else Orientation.AWAY_HOME
                )
            else:
                raise NotImplementedError(
                    """This 'meta_data' format is currently not supported..."""
                )

            if hasattr(meta_data, "HomeTeam") and hasattr(
                meta_data, "AwayTeam"
            ):
                home_team = self.create_team(
                    meta_data["HomeTeam"],
                    Ground.HOME,
                    start_frame_id=start_frame_id,
                    id_suffix=id_suffix,
                    player_item=player_item,
                )
                away_team = self.create_team(
                    meta_data["AwayTeam"],
                    Ground.AWAY,
                    start_frame_id=start_frame_id,
                    id_suffix=id_suffix,
                    player_item=player_item,
                )
            else:
                home_team = Team(
                    team_id="home", name="home", ground=Ground.HOME
                )
                away_team = Team(
                    team_id="away", name="away", ground=Ground.AWAY
                )
            teams = [home_team, away_team]

        with performance_logging("Loading data", logger=logger):
            transformer = self.get_transformer(
                pitch_length=pitch_size_width, pitch_width=pitch_size_height
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
                        if (
                            period_.start_timestamp
                            <= timedelta(seconds=frame_id / frame_rate)
                            <= period_.end_timestamp
                        ):
                            if n % sample == 0:
                                yield period_, line_
                            n += 1

            frames = []
            for n, (period, line) in enumerate(_iter()):
                frame = self._frame_from_line(teams, period, line, frame_rate)

                frame = transformer.transform_frame(frame)
                frames.append(frame)

                if self.limit and n >= self.limit:
                    break

        if not orientation:
            try:
                first_frame = next(
                    frame for frame in frames if frame.period.id == 1
                )
                orientation = (
                    Orientation.HOME_AWAY
                    if attacking_direction_from_frame(first_frame)
                    == AttackingDirection.LTR
                    else Orientation.AWAY_HOME
                )
            except StopIteration:
                warnings.warn(
                    "Could not determine orientation of dataset, defaulting to NOT_SET"
                )
                orientation = Orientation.NOT_SET

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
            date=date,
            game_id=game_id,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
