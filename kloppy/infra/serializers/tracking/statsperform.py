import logging
from typing import Dict, Optional, Union, NamedTuple, IO
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

from kloppy.utils import Readable, performance_logging

from .deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class StatsPerformInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class StatsPerformDeserializer(TrackingDataDeserializer[StatsPerformInputs]):
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
        period_data = {}
        for line in tracking:
            time_info = line.split(";")[1].split(",")
            period_id = int(time_info[1])
            frame_id = int(time_info[0])
            if period_id not in period_data:
                period_data[period_id] = set()
            period_data[period_id].add(frame_id)

        periods = {
            period_id: Period(
                id=period_id,
                start_timestamp=min(frame_ids),
                end_timestamp=max(frame_ids),
            )
            for period_id, frame_ids in period_data.items()
        }

        return periods

    @classmethod
    def __get_frame_rate(cls, tracking):
        """gets the frame rate of the tracking data"""

        frame_numbers = [
            int(line.split(";")[1].split(",")[0]) for line in tracking[1:]
        ]

        deltas = [
            frame_numbers[i + 1] - frame_numbers[i]
            for i in range(len(frame_numbers) - 1)
        ]

        most_common_delta = max(set(deltas), key=deltas.count)
        frame_rate = 1000 / most_common_delta

        return frame_rate

    @classmethod
    def _frame_from_framedata(cls, teams_list, period, frame_data):
        components = frame_data[1].split(":")
        frame_info = components[0].split(";")

        frame_id = int(frame_info[0])
        frame_timestamp = int(frame_info[1].split(",")[0]) / 1000
        match_status = int(frame_info[1].split(",")[2])

        ball_state = BallState.ALIVE if match_status == 0 else BallState.DEAD
        ball_owning_team = None

        if len(components) > 2:
            ball_data = components[2].split(";")[0].split(",")
            ball_x, ball_y, ball_z = map(float, ball_data)
            ball_coordinates = Point3D(ball_x, ball_y, ball_z)
        else:
            ball_coordinates = None

        players_data = {}
        player_info = components[1].split(";")[:-1]
        for player_data in player_info:
            player_data = player_data.split(",")

            team_side_id = int(player_data[0])
            player_id = player_data[1]
            jersey_no = int(player_data[2])
            x = float(player_data[3])
            y = float(player_data[4])

            # Goalkeepers have id 3 and 4
            if team_side_id > 2:
                team_side_id = team_side_id - 3
            team = teams_list[team_side_id]
            player = team.get_player_by_id(player_id)

            if not player:
                player = Player(
                    player_id=player_id,
                    team=team,
                    jersey_no=jersey_no,
                )
                team.players.append(player)

            players_data[player] = PlayerData(coordinates=Point(x, y))

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

    def deserialize(self, inputs: StatsPerformInputs) -> TrackingDataset:
        tracking = inputs.raw_data.read().decode("ascii").splitlines()
        metadata = inputs.meta_data.read()

        with performance_logging("Loading XML metadata", logger=logger):
            match = objectify.fromstring(metadata).matchInfo
            teams = {}
            for team_info in match.contestants.iterchildren(tag="contestant"):
                if team_info.attrib["position"] == "home":
                    ground = Ground.HOME
                else:
                    ground = Ground.AWAY
                team_id = team_info.attrib["id"]
                teams[team_id] = Team(
                    team_id=team_id,
                    name=team_info.attrib["name"],
                    ground=ground,
                )

            # Get Frame Rate - Either 10FPS or 25FPS
            frame_rate = self.__get_frame_rate(tracking)
            pitch_size_length = 100
            pitch_size_width = 100

            periods = self.__get_periods(tracking)
            # Get Player Info:
            for line_up in objectify.fromstring(
                metadata
            ).liveData.iterchildren(tag="lineUp"):
                team_id = line_up.get("contestantId")
                team = teams[team_id]

                for player in line_up.iterchildren(tag="player"):
                    player = player.attrib
                    player = Player(
                        player_id=player["playerId"],
                        name=player["matchName"],
                        starting=player["position"] == "substitute",
                        position=player["position"],
                        team=team,
                        jersey_no=player["shirtNumber"],
                        attributes={},
                    )
                    teams[team_id].players.append(player)

            teams_list = list(teams.values())
        # Handles the tracking frame data
        with performance_logging("Loading raw data", logger=logger):
            transformer = self.get_transformer(
                length=pitch_size_length, width=pitch_size_width
            )

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line_ in tracking:
                    splits = line_.split(";")[1].split(",")
                    frame_id = int(splits[0])
                    period_id = int(splits[1])
                    period_ = periods[period_id]
                    if period_.contains(frame_id / frame_rate):
                        if n % sample == 0:
                            yield period_, line_
                        n += 1

            frames = []
            for n, frame_data in enumerate(_iter(), start=1):
                period = frame_data[0]
                frame = self._frame_from_framedata(
                    teams_list, period, frame_data
                )
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
            if periods[1].attacking_direction == AttackingDirection.HOME_AWAY
            else Orientation.FIXED_AWAY_HOME
        )

        metadata = Metadata(
            teams=teams_list,
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
