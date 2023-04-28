import logging
from typing import Tuple, Dict, Optional, Union, NamedTuple, IO
from lxml import objectify
import numpy as np

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
    Position,
    Provider,
    PlayerData,
)

from kloppy.utils import Readable, performance_logging

from .deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class StatsperformInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]
    player_data: Optional[IO[bytes]] = None


class StatsperformDeserializer(
    TrackingDataDeserializer[StatsperformInputs]
):
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
        return Provider.STATSPERFORM

    @classmethod
    def __get_periods(cls, tracking):
        """gets the Periods contained in the tracking data"""
        periods = {}
        lines = tracking.decode("ascii").splitlines()
        _periods = []
        _frames = []
        for line in lines:
            time_info = line.split(";")[1].split(",")
            _periods.append(time_info[1])
            _frames.append(time_info[0])

        reversed_periods = _periods.copy()
        reversed_periods.reverse()
        unique_periods = list(dict.fromkeys(_periods))
        print(unique_periods)
        for period in unique_periods:
            period_start_index = _periods.index(period)
            period_end_index = len(_periods) - reversed_periods.index(period) - 1
            periods[period] = Period(
                id=period,
                start_timestamp=_frames[period_start_index],
                end_timestamp=_frames[period_end_index],
            )

        return periods


    @classmethod
    def _frame_from_framedata(cls, teams, period, frame_data):
        frame_id = frame_data["frameIdx"]
        frame_timestamp = frame_data["gameClock"]

        if frame_data["ball"]["xyz"]:
            ball_x, ball_y, ball_z = frame_data["ball"]["xyz"]
            ball_coordinates = Point3D(
                float(ball_x), float(ball_y), float(ball_z)
            )
        else:
            ball_coordinates = None

        ball_state = BallState.ALIVE if frame_data["live"] else BallState.DEAD
        ball_owning_team = (
            teams[0] if frame_data["lastTouch"] == "home" else teams[1]
        )

        players_data = {}
        for team, team_str in zip(teams, ["homePlayers", "awayPlayers"]):
            for player_data in frame_data[team_str]:

                jersey_no = player_data["number"]
                x, y, _ = player_data["xyz"]
                player = team.get_player_by_jersey_number(jersey_no)

                if not player:
                    player = Player(
                        player_id=player_data["playerId"],
                        team=team,
                        jersey_no=int(jersey_no),
                    )
                    team.players.append(player)

                players_data[player] = PlayerData(
                    coordinates=Point(float(x), float(y))
                )

        return Frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=ball_coordinates,
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            players_data=players_data,
            period=period,
            other_data={},
        )

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "xml_metadata" not in inputs:
            raise ValueError("Please specify a value for 'xml_metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    def deserialize(self, inputs: StatsperformInputs) -> TrackingDataset:
        raw_data = inputs.raw_data.read()
        metadata = inputs.meta_data.read()
        player_data = inputs.meta_data.read()

        with performance_logging("Loading XML metadata", logger=logger):
            periods = self.__get_periods(raw_data)

            match = objectify.fromstring(
                metadata
            ).matchInfo
            teams = []
            for team_info in match.contestants.iterchildren(tag="contestant"):
                if team_info.attrib["position"] == "home":
                    ground = Ground.HOME
                else:
                    ground = Ground.AWAY
                team = Team(
                    team_id=team_info.attrib["id"],
                    name=team_info.attrib["name"],
                    ground=ground,
                )
                teams.append(team)

            frame_rate = int(10)  # TODO: This should be changable based on whether the 10FPS or 25 FPS is loaded
            pitch_size_length = float(100)
            pitch_size_width = float(100)

        if inputs.player_data:
            with performance_logging("Loading JSON metadata", logger=logger):
                start_epoch_timestamp = int(raw_data.decode("ascii").splitlines()[0].split(";")[0])
                for player_info in player_data:
                    player = player_info.split(",")

                    player_position_id = int(player[1])
                    if player_position_id in [1, 3]:
                        team = teams[0]
                    elif player_position_id in [2, 4]:
                        team = teams[1]
                    position = "field player" if player_position_id in [1, 2] else "goalkeeper",
                    player = Player(
                        player_id=str(player[8]),
                        name=player[3],
                        starting=player[6] == start_epoch_timestamp,
                        # position= Position(
                        #                 #position_id=None,
                        #                 name=str(position),
                        #                 coordinates=None,
                        #             ),
                        team=team,
                        jersey_no=int(player[0]),
                        attributes={"statsUuid": int(player[8])},
                    )
                    team.players.append(player)

        # Handles the tracking frame data
        with performance_logging("Loading data", logger=logger): #TODO: LEFT HERE
            #TODO: Make this transformer work:
            transformer = self.get_transformer(
                length=pitch_size_length, width=pitch_size_width
            )

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line_ in raw_data.decode("ascii").splitlines():
                    frame_id = int(line_.split(";")[1].split(",")[0])
                    # if self.only_alive and not line_.endswith("Alive;:"):
                    #     continue

                    for period_ in periods:
                        print(period_)
                        print(frame_id)
                        print(frame_rate)
                        if period_.contains(frame_id / frame_rate):
                            if n % sample == 0:
                                yield period_, line_
                            n += 1

            # Hopelijk redelijk hetzelfde vanaf hier, alleen _frame_from_frame_data functie aanpassen.
            frames = []
            for n, frame_data in enumerate(_iter()):
                period = periods[frame_data["period"] - 1]
                frame = self._frame_from_framedata(teams, period, frame_data)
                #TODO: use transformer...
                #frame = transformer.transform_frame(frame)
                frames.append(frame)

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(
                            frame
                        )
                    )

                if self.limit and n + 1 >= self.limit:
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
            provider=Provider.STATSPERFORM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
