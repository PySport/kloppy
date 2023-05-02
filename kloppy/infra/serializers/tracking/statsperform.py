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


class StatsperformDeserializer(TrackingDataDeserializer[StatsperformInputs]):
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
        """Gets the Periods contained in the tracking data."""
        lines = tracking.decode("ascii").splitlines()
        period_ids = []
        frame_ids = []

        for line in lines:
            time_info = line.split(";")[1].split(",")
            period_ids.append(time_info[1])
            frame_ids.append(time_info[0])

        unique_period_ids = list(set(period_ids))
        periods = []

        for period_id in unique_period_ids:
            period_start_index = period_ids.index(period_id)
            period_end_index = (
                len(period_ids) - period_ids[::-1].index(period_id) - 1
            )
            periods.append(
                Period(
                    id=int(period_id),
                    start_timestamp=int(frame_ids[period_start_index]),
                    end_timestamp=int(frame_ids[period_end_index]),
                )
            )

        return periods

    @classmethod
    def __get_frame_rate(cls, tracking):
        """gets the frame rate of the tracking data"""
        lines = tracking.decode("ascii").splitlines()
        timestamps = []
        num_frames = 5

        for i in [0, num_frames]:
            timestamp = int(lines[i].split(";")[1].split(",")[0]) / 1000
            timestamps.append(timestamp)

        duration = timestamps[1] - timestamps[0]
        frame_rate = num_frames / duration

        return frame_rate

    @classmethod
    def _frame_from_framedata(cls, teams, period, frame_data):
        components = frame_data[1].split(":")
        frame_info = components[0].split(";")

        frame_id = int(frame_info[0])
        frame_timestamp = int(frame_info[1].split(",")[0]) / 1000
        match_status = int(frame_info[1].split(",")[2])

        ball_state = BallState.ALIVE if match_status == 0 else BallState.DEAD
        ball_owning_team = None

        if len(components) > 2:
            ball_x, ball_y, ball_z = map(
                float, components[2].split(";")[0].split(",")
            )
            ball_coordinates = Point3D(ball_x, ball_y, ball_z)
        else:
            ball_coordinates = np.nan

        players_data = {}
        player_info = components[1]
        for player_data in player_info.split(";")[:-1]:
            (
                team_side_id,
                player_id,
                jersey_no,
                x,
                y,
            ) = player_data.split(",")

            # Goalkeepers have id 3 and 4
            if int(team_side_id) > 2:
                team_side_id = int(team_side_id) - 3
            team = teams[int(team_side_id)]
            player = team.get_player_by_id(int(player_id))

            if not player:
                player = Player(
                    player_id=int(player_id),
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
            match = objectify.fromstring(metadata).matchInfo
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

            # Get Frame Rate - Either 10FPS or 25FPS
            frame_rate = self.__get_frame_rate(raw_data)
            pitch_size_length = 100
            pitch_size_width = 100

        periods = self.__get_periods(raw_data)

        if inputs.player_data:
            with performance_logging("Loading JSON metadata", logger=logger):
                start_epoch_timestamp = int(
                    raw_data.decode("ascii").splitlines()[0].split(";")[0]
                )
                for player_info in player_data:
                    player_data = player_info.split(",")
                    player = Player(
                        player_id=str(player_data[8]),
                        name=player_data[3],
                        starting=player_data[6] == start_epoch_timestamp,
                        team=team,
                        jersey_no=int(player_data[0]),
                        attributes={"statsUuid": int(player_data[8])},
                    )
                    team.players.append(player)

        # Handles the tracking frame data
        with performance_logging("Loading data", logger=logger):
            transformer = self.get_transformer(
                length=pitch_size_length, width=pitch_size_width
            )

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line_ in raw_data.decode("ascii").splitlines():
                    frame_id = int(line_.split(";")[1].split(",")[0])
                    if self.only_alive and not line_.endswith("Alive;:"):
                        continue
                    period_id = int(line_.split(";")[1].split(",")[1])
                    period_ = periods[period_id - 1]
                    if period_.contains(frame_id / frame_rate):
                        if n % sample == 0:
                            yield period_, line_
                        n += 1

            frames = []
            for n, frame_data in enumerate(_iter()):
                period = frame_data[0]
                frame = self._frame_from_framedata(teams, period, frame_data)
                frame = transformer.transform_frame(frame)
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
