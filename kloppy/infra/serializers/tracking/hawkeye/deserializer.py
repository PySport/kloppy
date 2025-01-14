import json
import logging
from datetime import datetime, timedelta
import warnings
from typing import (
    IO,
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Union,
    Iterable,
    Callable,
)
from itertools import zip_longest

from kloppy.domain import (
    AttackingDirection,
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
from kloppy.io import FileLike, open_as_file, get_file_extension
from kloppy.exceptions import DeserializationError

from ..deserializer import TrackingDataDeserializer

try:
    import tqdm
except ImportError:
    tqdm = None

logger = logging.getLogger(__name__)


class HawkEyeInputs(NamedTuple):
    ball_feeds: Iterable[FileLike]
    player_centroid_feeds: Iterable[FileLike]
    meta_data: Optional[FileLike] = None
    show_progress: Optional[bool] = False


class HawkEyeObjectIdentifier:
    FIFA_ID = 'fifaId'
    UEFA_ID = 'uefaId'
    HE_ID = 'heId'
    
    PRIORITY_IDS = [FIFA_ID, UEFA_ID, HE_ID]

class HawkEyeDeserializer(TrackingDataDeserializer[HawkEyeInputs]):
    def __init__(
        self,
        pitch_width: Optional[float] = 68.0,
        pitch_length: Optional[float] = 105.0,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive
        self.object_id: HawkEyeObjectIdentifier = None
        self.pitch_width = pitch_width
        self.pitch_length = pitch_length

    @property
    def provider(self) -> Provider:
        return Provider.HAWKEYE

    @staticmethod
    def __parse_periods(
        raw_periods: List[Dict[str, Any]]
    ) -> Dict[str, Period]:
        parsed_periods = {}
        for period in raw_periods:
            period_id = period["segment"]
            parsed_periods[period_id] = Period(
                id=period_id,
                start_timestamp=datetime.strptime(period["startTimeUTC"], '%Y-%m-%dT%H:%M:%S.%fZ'),
                end_timestamp=datetime.strptime(period["endTimeUTC"], '%Y-%m-%dT%H:%M:%S.%fZ'),
            )
        return parsed_periods

    def __parse_teams(self, raw_teams: List[Dict[str, Any]]) -> Dict[str, Team]:
        parsed_teams = {}
        for team in raw_teams:
            team_id = team["id"][self.object_id]
            parsed_teams[team_id] = Team(
                team_id=team["id"][self.object_id],
                name=team["name"],
                ground=Ground.HOME if team["home"] else Ground.AWAY,
            )
        return parsed_teams

    def __parse_players(
        self, raw_players: List[Dict[str, Any]], teams: Dict[str, Team]
    ) -> Dict[str, Player]:
        parsed_players = {}
        for player in raw_players:
            player_id = player["id"][self.object_id]
            parsed_players[player_id] = Player(
                player_id=player["id"][self.object_id],
                team=teams[player["teamId"][self.object_id]],
                jersey_no=int(player["jerseyNumber"]),
                starting_position=player["role"]["name"],
            )
        return parsed_players
    
    def __get_identifier_variable(self, player_tracking_data):
        player_object = player_tracking_data['details']['players'][0]['id']
        
        for identifier in HawkEyeObjectIdentifier.PRIORITY_IDS:
            if player_object.get(identifier):
                self.object_id = identifier
                return
        
        self.object_id = HawkEyeObjectIdentifier.HE_ID
    
    @staticmethod
    def __infer_frame_rate(ball_tracking_data, n_samples=25):
        total_time_difference = 0

        for i in range(len(ball_tracking_data["samples"]["ball"]) - 1):
            current_time = ball_tracking_data["samples"]["ball"][i]["time"]
            next_time = ball_tracking_data["samples"]["ball"][i + 1]["time"]
            
            time_difference = next_time - current_time
            total_time_difference += time_difference
            
            if i >= n_samples - 1:
                break
            
        return int(1 / (total_time_difference / n_samples))
    
    @staticmethod
    def __parse_meta_data(meta_data):
        if meta_data is None:
            return 
            
        meta_data_extension = get_file_extension(meta_data)
        
    def deserialize(self, inputs: HawkEyeInputs) -> TrackingDataset:
        
        self.__parse_meta_data(inputs.meta_data)
            
        transformer = self.get_transformer(
            pitch_length=self.pitch_length,
            pitch_width=self.pitch_width,
        )
        

        parsed_teams = {}
        parsed_players = {}
        parsed_periods = {}
        parsed_periods = {}
        parsed_frames = {}
        frame_rate = None

        it = list(zip_longest(inputs.ball_feeds, inputs.player_centroid_feeds))
        if inputs.show_progress:
            if tqdm is None:
                warnings.warn(
                    "tqdm not installed, progress bar will not be shown"
                )
            else:
                it = tqdm.tqdm(it)

        for ball_feed, player_centroid_feed in it:
            # Read the ball and player tracking data feeds.
            with open_as_file(ball_feed) as ball_data_fp:
                ball_tracking_data = json.load(ball_data_fp)
            with open_as_file(player_centroid_feed) as player_centroid_data_fp:
                player_tracking_data = json.load(player_centroid_data_fp)
            
            if frame_rate is not None:
                frame_rate = self.__infer_frame_rate(ball_tracking_data)
            self.__get_identifier_variable(player_tracking_data)
            
            # Parse the teams, players and periods. A value can be added by
            # later feeds, but we will not overwrite existing values.
            with performance_logging("Parsing meta data", logger=logger):
                parsed_teams = {
                    **self.__parse_teams(
                        ball_tracking_data["details"]["teams"]
                    ),
                    **parsed_teams,
                }
                parsed_players = {
                    **self.__parse_players(
                        player_tracking_data["details"]["players"],
                        parsed_teams,
                    ),
                    **parsed_players,
                }
                parsed_periods = {
                    **self.__parse_periods(ball_tracking_data["segments"]),
                    **parsed_periods,
                }
                
            
            # Parse the ball tracking data
            period_id = ball_tracking_data["sequences"]["segment"]
            minute = ball_tracking_data["sequences"]["match-minute"] - 1
            with performance_logging(
                "Parsing ball tracking data", logger=logger
            ):
                for detection in ball_tracking_data["samples"]["ball"]:
                    frame_id = int(
                        (minute * 60 + detection["time"]) * frame_rate
                    )
                    parsed_frames[frame_id] = Frame(
                        frame_id=frame_id,
                        timestamp=timedelta(
                            minutes=minute, seconds=detection["time"]
                        ),
                        ball_coordinates=Point3D(
                            x=detection["pos"][0],
                            y=detection["pos"][1],
                            z=detection["pos"][2],
                        ),
                        ball_speed=detection["speed"]["mps"],
                        ball_state=None,
                        ball_owning_team=None,
                        players_data={},
                        period=parsed_periods[period_id],
                        other_data={},
                    )

            # Parse the player tracking data
            _period_id = player_tracking_data["sequences"]["segment"]
            _minute = player_tracking_data["sequences"]["match-minute"] - 1
            
            if _period_id != period_id or _minute != minute:
                raise DeserializationError(
                    "The feed for ball tracking and player tracking are not in sync"
                )
            with performance_logging(
                "Parsing player tracking data", logger=logger
            ):
                for detection in player_tracking_data["samples"]["people"]:
                    if detection["role"]["name"] not in [
                        "Outfielder",
                        "Goalkeeper",
                    ]:
                        continue
                    player = parsed_players[detection["personId"][self.object_id]]
                    for centroid in detection["centroid"]:
                        frame_id = int(
                            (minute * 60 + centroid["time"]) * frame_rate
                        )
                        player_data = PlayerData(
                            coordinates=Point(
                                x=centroid["pos"][0],
                                y=centroid["pos"][1],
                            ),
                            distance=centroid["distance"]["metres"],
                            speed=centroid["speed"]["mps"],
                        )
                        if frame_id in parsed_frames:
                            parsed_frames[frame_id].players_data[
                                player
                            ] = player_data
                        else:
                            parsed_frames[frame_id] = Frame(
                                frame_id=frame_id,
                                timestamp=timedelta(
                                    minutes=minute, seconds=centroid["time"]
                                ),
                                ball_coordinates=Point3D(
                                    float("nan"), float("nan"), float("nan")
                                ),
                                ball_state=None,
                                ball_owning_team=None,
                                players_data={player: player_data},
                                period=parsed_periods[period_id],
                                other_data={},
                            )

            if self.limit and len(parsed_frames) >= self.limit:
                break

        # Convert the parsed frames to a list
        frame_ts = sorted(parsed_frames.keys())
        frames = []
        sample = 1.0 / self.sample_rate
        for ts in frame_ts:
            idx = int(ts * frame_rate)
            if idx % sample == 0:
                frame = transformer.transform_frame(parsed_frames[ts])
                frames.append(frame)

                if self.limit and idx >= self.limit:
                    break

        # Add player list to teams
        for team in parsed_teams.values():
            for player in parsed_players.values():
                if player.team == team:
                    team.players.append(player)

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
            teams=list(parsed_teams.values()),
            periods=list(parsed_periods.values()),
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=None,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.HAWKEYE,
            flags=None,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(
            records=frames,
            metadata=meta_data,
        )
