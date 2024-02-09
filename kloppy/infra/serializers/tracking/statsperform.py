import json
import logging
from datetime import datetime, timedelta
import warnings
from typing import IO, Any, Dict, List, NamedTuple, Optional, Union

from lxml import objectify

from kloppy.domain import (
    AttackingDirection,
    BallState,
    DatasetFlag,
    Frame,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    PlayerData,
    Point,
    Point3D,
    Provider,
    Team,
    TrackingDataset,
    attacking_direction_from_frame,
)
from kloppy.utils import performance_logging

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
        frame_timestamp = timedelta(
            seconds=int(frame_info[1].split(",")[0]) / 1000
        )
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
    def __parse_periods_from_xml(match: Any) -> List[Dict[str, Any]]:
        parsed_periods = []
        live_data = match.liveData
        match_details = live_data.matchDetails
        periods = match_details.periods
        for period in periods.iterchildren(tag="period"):
            parsed_periods.append(
                {
                    "id": int(period.get("id")),
                    "start_timestamp": datetime.strptime(
                        period.get("start"), "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "end_timestamp": datetime.strptime(
                        period.get("end"), "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
        return parsed_periods

    @staticmethod
    def __parse_teams_from_xml(match: Any) -> List[Dict[str, Any]]:
        parsed_teams = []
        match_info = match.matchInfo
        teams = match_info.contestants.iterchildren(tag="contestant")
        for team in teams:
            team_attributes = team.attrib
            team_id = team_attributes["id"]
            parsed_teams.append(
                {
                    "team_id": team_id,
                    "name": team_attributes["name"],
                    "ground": team_attributes["position"],
                }
            )
        return parsed_teams

    @staticmethod
    def __parse_players_from_xml(match: Any) -> List[Dict[str, Any]]:
        parsed_players = []
        live_data = match.liveData
        line_ups = live_data.iterchildren(tag="lineUp")
        for line_up in line_ups:
            team_id = line_up.get("contestantId")
            players = line_up.iterchildren(tag="player")
            for player in players:
                player_attributes = player.attrib
                player_id = player_attributes["playerId"]
                parsed_players.append(
                    {
                        "player_id": player_id,
                        "team_id": team_id,
                        "jersey_no": int(player_attributes["shirtNumber"]),
                        "name": player_attributes["matchName"],
                        "first_name": player_attributes["shortFirstName"],
                        "last_name": player_attributes["shortLastName"],
                        "starting": player_attributes["position"]
                        != "Substitute",
                        "position": player_attributes["position"],
                    }
                )
        return parsed_players

    @staticmethod
    def __parse_periods_from_json(
        match: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        parsed_periods = []
        live_data = match["liveData"]
        match_details = live_data["matchDetails"]
        periods = match_details["period"]
        for period in periods:
            parsed_periods.append(
                {
                    "id": period["id"],
                    "start_timestamp": datetime.strptime(
                        period["start"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "end_timestamp": datetime.strptime(
                        period["end"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
            )
        return parsed_periods

    @staticmethod
    def __parse_teams_from_json(match: Dict[str, Any]) -> List[Dict[str, Any]]:
        parsed_teams = []
        match_info = match["matchInfo"]
        teams = match_info["contestant"]
        for team in teams:
            team_id = team["id"]
            parsed_teams.append(
                {
                    "team_id": team_id,
                    "name": team["name"],
                    "ground": team["position"],
                }
            )
        return parsed_teams

    @staticmethod
    def __parse_players_from_json(
        match: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        parsed_players = []
        live_data = match["liveData"]
        line_ups = live_data["lineUp"]
        for line_up in line_ups:
            team_id = line_up["contestantId"]
            players = line_up["player"]
            for player in players:
                player_id = player["playerId"]
                parsed_players.append(
                    {
                        "player_id": player_id,
                        "team_id": team_id,
                        "jersey_no": player["shirtNumber"],
                        "name": player["matchName"],
                        "first_name": player["shortFirstName"],
                        "last_name": player["shortLastName"],
                        "starting": player["position"] != "Substitute",
                        "position": player["position"],
                    }
                )
        return parsed_players

    def deserialize(self, inputs: StatsPerformInputs) -> TrackingDataset:
        tracking_data = inputs.raw_data.read().decode("ascii").splitlines()
        meta_data = inputs.meta_data.read()

        with performance_logging("Loading meta data", logger=logger):
            if meta_data.decode("utf-8")[0] == "<":
                match = objectify.fromstring(meta_data)
                parsed_periods = self.__parse_periods_from_xml(match)
                parsed_teams = self.__parse_teams_from_xml(match)
                parsed_players = self.__parse_players_from_xml(match)
            else:
                match = json.loads(meta_data)
                parsed_periods = self.__parse_periods_from_json(match)
                parsed_teams = self.__parse_teams_from_json(match)
                parsed_players = self.__parse_players_from_json(match)

            periods = {}
            for parsed_period in parsed_periods:
                period_id = parsed_period["id"]
                periods[period_id] = Period(
                    id=period_id,
                    start_timestamp=parsed_period["start_timestamp"],
                    end_timestamp=parsed_period["end_timestamp"],
                )

            teams = {}
            for parsed_team in parsed_teams:
                team_id = parsed_team["team_id"]
                teams[team_id] = Team(
                    team_id=team_id,
                    name=parsed_team["name"],
                    ground=Ground.HOME
                    if parsed_team["ground"] == "home"
                    else Ground.AWAY,
                )

            for parsed_player in parsed_players:
                player_id = parsed_player["player_id"]
                team_id = parsed_player["team_id"]
                team = teams[team_id]
                player = Player(
                    player_id=player_id,
                    team=team,
                    jersey_no=parsed_player["jersey_no"],
                    name=parsed_player["name"],
                    first_name=parsed_player["first_name"],
                    last_name=parsed_player["last_name"],
                    starting=parsed_player["starting"],
                    position=parsed_player["position"],
                )
                team.players.append(player)
            teams_list = list(teams.values())

        with performance_logging("Loading tracking data", logger=logger):
            frame_rate = self.__get_frame_rate(tracking_data)
            pitch_size_length = 100
            pitch_size_width = 100

            transformer = self.get_transformer(
                length=pitch_size_length,
                width=pitch_size_width,
            )

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line_ in tracking_data:
                    splits = line_.split(";")[1].split(",")
                    period_id = int(splits[1])
                    period_ = periods[period_id]
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

                if self.limit and n >= self.limit:
                    break

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

        meta_data = Metadata(
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
            metadata=meta_data,
        )
