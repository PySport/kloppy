import json
import logging
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import warnings
import re
from lxml import objectify

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
    FIFA_ID = "fifaId"
    UEFA_ID = "uefaId"
    HE_ID = "heId"

    PRIORITY_IDS = [FIFA_ID, UEFA_ID, HE_ID]

    @classmethod
    def get_identifier_variable(cls, player_tracking_data):
        player_object = player_tracking_data["details"]["players"][0]["id"]

        object_id = cls.HE_ID
        for identifier in cls.PRIORITY_IDS:
            if player_object.get(identifier):
                return identifier
        return object_id


class HawkEyeDeserializer(TrackingDataDeserializer[HawkEyeInputs]):
    def __init__(
        self,
        pitch_width: Optional[float] = 68.0,
        pitch_length: Optional[float] = 105.0,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.object_id: HawkEyeObjectIdentifier = None
        self.pitch_width = pitch_width
        self.pitch_length = pitch_length

        self._game_id = None
        self._game_week = None
        self._game_date = None

    @property
    def provider(self) -> Provider:
        return Provider.HAWKEYE

    @staticmethod
    def __parse_periods(
        raw_periods: List[Dict[str, Any]]
    ) -> Dict[str, Period]:
        parsed_periods = {}
        for period in raw_periods:
            if period["segment"] == 0:
                continue
            period_id = period["segment"]

            parsed_periods[period_id] = Period(
                id=period_id,
                start_timestamp=datetime.strptime(
                    period["startTimeUTC"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ),
                end_timestamp=datetime.strptime(
                    period["endTimeUTC"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ),
            )
        return parsed_periods

    def __parse_teams(
        self, raw_teams: List[Dict[str, Any]]
    ) -> Dict[str, Team]:
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

    def __parse_meta_data_json(self, meta_data):
        with open_as_file(meta_data) as meta_data_fp:
            meta_data = json.load(meta_data_fp)

        kick_off_time = meta_data.get("KickOffTime")
        match_day = re.search(r"\d+", meta_data.get("MatchDay"))
        game_week = match_day.group() if match_day else None

        stadium = meta_data.get("Stadium")
        self.pitch_length = (
            stadium.get("PitchLength", self.pitch_length)
            if stadium
            else self.pitch_length
        )
        self.pitch_width = (
            stadium.get("PitchWidth", self.pitch_width)
            if stadium
            else self.pitch_width
        )

        self._game_id = meta_data.get("MatchId")
        self._game_date = (
            parse(kick_off_time.get("DateTime")).replace(tzinfo=timezone.utc)
            if kick_off_time
            else None
        )
        self._game_week = game_week

    def __parse_meta_data_xml(self, meta_data):
        with open_as_file(meta_data) as meta_data_fp:
            root = objectify.fromstring(meta_data_fp.read())

        game_id = getattr(root, "id", None)
        date = (
            getattr(root.kickOffTime, "dateTime", None)
            if hasattr(root, "kickOffTime")
            else None
        )
        game_week_attr = (
            getattr(root.matchday, "name", None)
            if hasattr(root, "matchday")
            else None
        )
        self.pitch_length = (
            getattr(root.stadium.pitch, "length", self.pitch_length)
            if hasattr(root.stadium, "pitch")
            else self.pitch_length
        )
        self.pitch_width = (
            getattr(root.stadium.pitch, "width", self.pitch_width)
            if hasattr(root.stadium, "pitch")
            else self.pitch_width
        )

        if date:
            date = parse(str(date)).replace(tzinfo=timezone.utc)
        if game_week_attr:
            match_day = re.search(r"\d+", str(game_week_attr))
            game_week = match_day.group() if match_day else None

        self._game_id = str(game_id) if game_id else None
        self._game_date = date
        self._game_week = game_week

    def __parse_meta_data(self, meta_data):
        if meta_data is None:
            return

        meta_data_extension = get_file_extension(meta_data)
        if meta_data_extension == ".xml":
            return self.__parse_meta_data_xml(meta_data)
        elif meta_data_extension == ".json":
            return self.__parse_meta_data_json(meta_data)
        else:
            raise ValueError(
                "Metadata only supports .json and .xml file formats..."
            )

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

            self.object_id = HawkEyeObjectIdentifier.get_identifier_variable(
                player_tracking_data
            )

            if frame_rate is None:
                frame_rate = self.__infer_frame_rate(ball_tracking_data)

            if not self._game_id:
                self._game_id = ball_tracking_data["details"]["match"]["id"][
                    self.object_id
                ]

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

            period_minute = (
                minute
                if period_id == 1
                else (minute - 45)
                if period_id == 2
                else (minute - 90)
                if period_id == 3
                else (minute - 105)
                if period_id == 4
                else (minute - 120)
            )

            with performance_logging(
                "Parsing ball tracking data", logger=logger
            ):
                for detection in ball_tracking_data["samples"]["ball"]:
                    frame_id = int(
                        (minute * 60 + float(detection["time"])) * frame_rate
                    )
                    parsed_frames[frame_id] = Frame(
                        frame_id=frame_id,
                        timestamp=timedelta(
                            minutes=period_minute, seconds=detection["time"]
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
                        statistics=[],
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
                    player = parsed_players[
                        detection["personId"][self.object_id]
                    ]
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
                                    minutes=period_minute,
                                    seconds=centroid["time"],
                                ),
                                ball_coordinates=Point3D(
                                    float("nan"), float("nan"), float("nan")
                                ),
                                ball_state=None,
                                ball_owning_team=None,
                                players_data={player: player_data},
                                period=parsed_periods[period_id],
                                other_data={},
                                statistics=[],
                            )

            if self.limit and len(parsed_frames) >= self.limit:
                break

        # Convert the parsed frames to a list
        frame_ts = sorted(parsed_frames.keys())
        frames = []
        sample = 1.0 / self.sample_rate
        for i, ts in enumerate(frame_ts):
            if ts % sample == 0:
                frame = transformer.transform_frame(parsed_frames[ts])
                frames.append(frame)

                if self.limit and i * (self.sample_rate) + 1 >= self.limit:
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
            game_id=self._game_id,
            date=self._game_date,
            game_week=self._game_week,
        )

        return TrackingDataset(
            records=frames,
            metadata=meta_data,
        )
