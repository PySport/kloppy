import json
import logging
from collections import defaultdict
from datetime import timedelta, timezone
from typing import IO, Dict, NamedTuple, Optional, Union, List
import warnings

from dateutil.parser import parse

from kloppy.domain import (
    BallState,
    DatasetFlag,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    PlayerData,
    Point,
    Point3D,
    PositionType,
    Provider,
    Team,
    TrackingDataset,
    AttackingDirection,
    Frame,
)

from kloppy.domain.services.frame_factory import create_frame
from kloppy.domain.services import attacking_direction_from_frame
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)


position_types_mapping: Dict[str, PositionType] = {
    "CB": PositionType.CenterBack,
    "LCB": PositionType.LeftCenterBack,
    "RCB": PositionType.RightCenterBack,
    "LB": PositionType.LeftBack,
    "RB": PositionType.RightBack,
    "DM": PositionType.DefensiveMidfield,
    "CM": PositionType.CenterMidfield,
    "LW": PositionType.LeftWing,
    "RW": PositionType.RightWing,
    "D": PositionType.Defender,
    "CF": PositionType.Striker,
    "M": PositionType.Midfielder,
    "AM": PositionType.AttackingMidfield,
    "GK": PositionType.Goalkeeper,
    "F": PositionType.Attacker,
}


class GameEventType:
    """
    GameEventType

    Type of game event.

    Attributes:
        FIRST_KICK_OFF: First half kick-off.
        SECOND_KICK_OFF: Second half kick-off.
        THIRD_KICK_OFF: Third half kick-off (if applicable).
        FOURTH_KICK_OFF: Fourth half kick-off (if applicable).
        PERIOD_END: End of half.
        STAYS_IN_PLAY: Ball hits post, bar, or corner flag and stays in play.
        PLAYER_OFF: Player off.
        PLAYER_ON: Player on.
        ON_THE_BALL: On-the-ball event.
        BALL_OUT: Ball out-of-play.
        SUBSTITUTION: Substitution event.
        VIDEO_MISSING: Video data missing.
    """

    FIRST_KICK_OFF = "FIRSTKICKOFF"
    SECOND_KICK_OFF = "SECONDKICKOFF"
    THIRD_KICK_OFF = "THIRDKICKOFF"
    FOURTH_KICK_OFF = "FOURTHKICKOFF"
    PERIOD_END = "END"
    STAYS_IN_PLAY = "G"
    PLAYER_OFF = "OFF"
    PLAYER_ON = "ON"
    ON_THE_BALL = "OTB"
    BALL_OUT = "OUT"
    SUBSTITUTION = "SUB"
    VIDEO_MISSING = "VID"


class PFF_TrackingInputs(NamedTuple):
    meta_data: IO[bytes]
    roster_meta_data: IO[bytes]
    raw_data: IO[bytes]


class PFF_TrackingDeserializer(TrackingDataDeserializer[PFF_TrackingInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = False,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

        self._ball_owning_team = None
        self._ball_state = BallState.DEAD

    @property
    def provider(self) -> Provider:
        return Provider.PFF

    @classmethod
    def _get_frame_data(
        cls,
        players,
        periods,
        ball_owning_team,
        ball_state,
        frame,
    ):
        """Gets a Frame"""

        # Get Frame information
        frame_period = frame["period"]
        frame_id = frame["frameNum"]
        frame_timestamp = timedelta(seconds=frame["periodElapsedTime"])

        # Ball coordinates
        ball_smoothed = frame.get("ballsSmoothed")
        if ball_smoothed:
            ball_x = ball_smoothed.get("x")
            ball_y = ball_smoothed.get("y")
            ball_z = ball_smoothed.get("z")

            if ball_x is None or ball_y is None:
                ball_coordinates = None
            else:
                ball_coordinates = Point3D(
                    x=float(ball_x),
                    y=float(ball_y),
                    z=float(ball_z) if ball_z is not None else None,
                )

        else:
            ball_coordinates = None

        # Player coordinates
        players_data = {}

        # Helper function to map players
        def map_players(players_smoothed, team):
            if players_smoothed is None:
                return

            for player_info in players_smoothed:
                jersey_num = int(player_info.get("jerseyNum"))
                player = next(
                    (
                        p
                        for p in players[team].values()
                        if p.jersey_no == jersey_num
                    ),
                    None,
                )

                if player:
                    player_x = player_info.get("x")
                    player_y = player_info.get("y")

                    if player_x is not None and player_y is not None:
                        player_data = PlayerData(
                            coordinates=Point(player_x, player_y)
                        )
                        players_data[player] = player_data

        # Process home and away players
        map_players(frame.get("homePlayersSmoothed"), "HOME")
        map_players(frame.get("awayPlayersSmoothed"), "AWAY")

        return create_frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=ball_coordinates,
            players_data=players_data,
            period=periods[frame_period],
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            other_data={},
        )

    @classmethod
    def __get_periods(cls, tracking, frame_rate):
        """Gets the Periods contained in the tracking data"""
        periods = {}
        frames_by_period = defaultdict(list)

        for raw_frame in tracking:
            frame = json.loads(raw_frame)
            if frame["period"] is not None:
                frames_by_period[frame["period"]].append(frame)

        for period, frames in frames_by_period.items():
            periods[period] = Period(
                id=period,
                start_timestamp=timedelta(
                    seconds=frames[0]["frameNum"] / frame_rate
                ),
                end_timestamp=timedelta(
                    seconds=frames[-1]["frameNum"] / frame_rate
                ),
            )

        return periods

    def deserialize(self, inputs: PFF_TrackingInputs) -> TrackingDataset:
        # Load datasets
        metadata = json.load(inputs.meta_data)[0]
        roster_meta_data = json.load(inputs.roster_meta_data)
        raw_data = inputs.raw_data.readlines()

        # Obtain game_id from metadata
        game_id = int(metadata["id"])

        if not metadata:
            raise DeserializationError(
                "The game_id of this game is not contained within the provided meta data file"
            )

        # Get metadata variables
        home_team = metadata["homeTeam"]
        away_team = metadata["awayTeam"]
        stadium = metadata["stadium"]
        game_week = metadata["week"]

        # Obtain frame rate
        frame_rate = metadata["fps"]

        home_team_id = home_team["id"]
        away_team_id = away_team["id"]

        with performance_logging("Loading metadata", logger=logger):
            periods = self.__get_periods(raw_data, frame_rate)

            pitch_size_width = stadium["pitches"][0]["width"]
            pitch_size_length = stadium["pitches"][0]["length"]

            transformer = self.get_transformer(
                pitch_length=pitch_size_length, pitch_width=pitch_size_width
            )

            date = metadata.get("date")

            if date:
                date = parse(date).replace(tzinfo=timezone.utc)

            players = {"HOME": {}, "AWAY": {}}

            # Create Team objects for home and away sides
            home_team = Team(
                team_id=home_team_id,
                name=home_team["name"],
                ground=Ground.HOME,
            )
            away_team = Team(
                team_id=away_team_id,
                name=away_team["name"],
                ground=Ground.AWAY,
            )
            teams = [home_team, away_team]

            for player in roster_meta_data:

                team_id = player["team"]["id"]
                player_col = player["player"]

                player_id = player_col["id"]
                player_name = player_col["nickname"]
                shirt_number = int(player["shirtNumber"])
                player_position = player["positionGroupType"]

                if team_id == home_team_id:
                    team_string = "HOME"
                    team = home_team
                elif team_id == away_team_id:
                    team_string = "AWAY"
                    team = away_team
                else:
                    raise DeserializationError(f"Unknown team_id: {team_id}")

                # Create Player object
                players[team_string][player_id] = Player(
                    player_id=player_id,
                    team=team,
                    jersey_no=shirt_number,
                    name=player_name,
                    starting_position=position_types_mapping.get(
                        player_position, PositionType.Unknown
                    ),
                    starting=None,
                )

            home_team.players = list(players["HOME"].values())
            away_team.players = list(players["AWAY"].values())

        with performance_logging("Loading data", logger=logger):

            def _iter():
                sample = 1.0 / self.sample_rate

                n = 0

                for raw_frame in raw_data:
                    frame = json.loads(raw_frame)
                    # Identify Period
                    frame_period = frame.get("period")

                    # Find ball owning team
                    game_event = frame.get("game_event")

                    if game_event:
                        game_event_type = game_event.get("game_event_type")

                        if game_event_type in (
                            GameEventType.BALL_OUT,
                            GameEventType.PERIOD_END,
                        ):
                            self._ball_state = BallState.DEAD
                        elif game_event_type in (
                            GameEventType.FIRST_KICK_OFF,
                            GameEventType.SECOND_KICK_OFF,
                            GameEventType.THIRD_KICK_OFF,
                            GameEventType.FOURTH_KICK_OFF,
                            GameEventType.ON_THE_BALL,
                        ):
                            self._ball_state = BallState.ALIVE
                        else:
                            # for other events leave ball state as is
                            pass

                        if game_event.get("home_ball") is not None:
                            self._ball_owning_team = (
                                home_team
                                if game_event["home_ball"]
                                else away_team
                            )

                    if self.only_alive and self._ball_state == BallState.DEAD:
                        continue

                    if frame_period is not None and n % sample == 0:
                        yield frame, frame_period

                    n += 1

        frames, et_frames = [], []
        n_frames = 0

        for _frame, _frame_period in _iter():
            # Create and transform Frame object
            frame = transformer.transform_frame(
                self._get_frame_data(
                    players,
                    periods,
                    self._ball_owning_team,
                    self._ball_state,
                    _frame,
                )
            )

            # if Regular Time
            if _frame_period in {1, 2}:
                frames.append(frame)

            # else if extra time
            elif _frame_period in {3, 4}:
                et_frames.append(frame)

            n_frames += 1

            if self.limit and n_frames >= self.limit:
                break

        first_frame_p1 = next(
            frame for frame in frames if frame.period.id == 1
        )
        is_home_team_left = (
            True
            if attacking_direction_from_frame(first_frame_p1)
            == AttackingDirection.LTR
            else False
        )

        if et_frames:
            first_frame_p3 = next(
                frame for frame in et_frames if frame.period.id == 3
            )
            is_home_team_extra_time_left = (
                True
                if attacking_direction_from_frame(first_frame_p3)
                == AttackingDirection.LTR
                else False
            )
            # If first period and third period attacking direction for home team is inconsistent, flip the direction of the extra time frames
            if is_home_team_left != is_home_team_extra_time_left:
                for et_frame in et_frames:
                    # Loop through each PlayerData in the players_data dictionary
                    for _, player_data in et_frame.players_data.items():
                        if (
                            player_data.coordinates
                            and player_data.coordinates.x is not None
                            and player_data.coordinates.y is not None
                        ):
                            # Create a new Point with multiplied coordinates for each player
                            player_data.coordinates = Point(
                                -player_data.coordinates.x,
                                -player_data.coordinates.y,
                            )

                    # Multiply the x and y coordinates of the ball by -1
                    if (
                        et_frame.ball_coordinates
                        and et_frame.ball_coordinates.x is not None
                        and et_frame.ball_coordinates.y is not None
                    ):
                        et_frame.ball_coordinates = Point3D(
                            -et_frame.ball_coordinates.x,
                            -et_frame.ball_coordinates.y,
                            et_frame.ball_coordinates.z,
                        )

        orientation = (
            Orientation.HOME_AWAY
            if is_home_team_left
            else Orientation.AWAY_HOME
        )

        frames.extend(et_frames)

        metadata = Metadata(
            teams=teams,
            periods=sorted(periods.values(), key=lambda p: p.id),
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.PFF,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
            date=date,
            game_id=game_id,
            game_week=game_week,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
