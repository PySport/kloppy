import json
import logging
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import IO, Dict, NamedTuple, Optional, Union

from kloppy.domain import (
    AttackingDirection,
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
    Score,
    Team,
    TrackingDataset,
    attacking_direction_from_frame,
)
from kloppy.domain.services.frame_factory import create_frame
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)


class RespoVisionInputs(NamedTuple):
    raw_data: IO[bytes]


class RespoVisionDeserializer(TrackingDataDeserializer[RespoVisionInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        include_empty_frames: Optional[bool] = False,
        pitch_width: Optional[float] = 68.0,
        pitch_length: Optional[float] = 105.0,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.include_empty_frames = include_empty_frames
        self.pitch_width = pitch_width
        self.pitch_length = pitch_length

    @property
    def provider(self) -> Provider:
        return Provider.RESPOVISION

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
    def _timestamp_from_timestring(cls, timestring):
        m, s = timestring.split(":")
        return 60 * float(m) + float(s)

    @classmethod
    def _set_skillcorner_attacking_directions(cls, frames, periods):
        """
        with only partial tracking data we cannot rely on a single frame to
        infer the attacking directions as a simple average of only some players
        x-coords might not reflect the attacking direction.
        """
        attacking_directions = []

        for frame in frames:
            if len(frame.players_data) > 0:
                attacking_directions.append(
                    attacking_direction_from_frame(frame)
                )
            else:
                attacking_directions.append(AttackingDirection.NOT_SET)

        frame_periods = np.array([_frame.period.id for _frame in frames])

        for period in periods.keys():
            if period in frame_periods:
                count = Counter(
                    np.array(attacking_directions)[frame_periods == period]
                )
                att_direction = count.most_common()[0][0]
                periods[period].attacking_direction = att_direction
            else:
                periods[
                    period
                ].attacking_direction = AttackingDirection.NOT_SET

    def __load_json(self, file):
        return json.load(file)

    @classmethod
    def __get_periods(cls, tracking):
        """gets the Periods contained in the tracking data"""
        periods = {}

        _periods = np.array([f["period"] for f in tracking])
        unique_periods = set(_periods)
        unique_periods = [
            period for period in unique_periods if period is not None
        ]

        for period in unique_periods:
            _frames = [
                frame
                for frame in tracking
                if frame["period"] == period and frame["time"] is not None
            ]

            periods[period] = Period(
                id=period,
                start_timestamp=cls._timestamp_from_timestring(
                    _frames[0]["time"]
                ),
                end_timestamp=cls._timestamp_from_timestring(
                    _frames[-1]["time"]
                ),
            )
        return periods

    @classmethod
    def __create_anon_player(cls, teams, frame_record):
        """
        creates a Player object for a track_id'ed player with known team membership but unknown identity.

        Args:
            frame_record (dict): dictionary containing 'x', 'y', 'track_id' and 'group_name'

        Returns:
            kloppy.domain.models.common.Player

        """
        track_id = frame_record.get("track_id", None)
        group_name = frame_record.get("group_name", None)

        if group_name == "home team":
            team = teams[0]
        elif group_name == "away team":
            team = teams[1]
        else:
            raise ValueError(
                f"anonymous player with track_id `{track_id}` does not have a specified group_name."
            )

        return Player(
            player_id=f"{team.ground}_anon_{track_id}",
            team=team,
            jersey_no=None,
            name=f"Anon_{track_id}",
            first_name="Anon",
            last_name=track_id,
            starting=None,
            position=None,
            attributes={},
        )

    def _extract_teams(self, frame):
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

    def deserialize(self, inputs: RespoVisionInputs) -> TrackingDataset:
        raw_data = inputs.raw_data

        transformer = self.get_transformer(
            pitch_length=self.pitch_length, pitch_width=self.pitch_width
        )

        with performance_logging("Loading data", logger=logger):

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for line in raw_data:
                    frame = json.loads(line)
                    frame_period = frame["period"]

                    if frame_period is not None:
                        if n % sample == 0:
                            yield frame
                        n += 1

        n_frames = 0
        frames = []

        for _frame in _iter():
            _extract_players(_frame)
            _extract_period()
            _extract_teams()

            if self.include_empty_frames or len(_frame["data"]) > 0:
                frame = self._get_frame_data(
                    teams,
                    teamdict,
                    players,
                    player_to_team_dict,
                    periods,
                    player_dict,
                    anon_players,
                    ball_id,
                    referee_dict,
                    _frame,
                )

                frame = transformer.transform_frame(frame)

                frames.append(frame)
                n_frames += 1

                if self.limit and n_frames >= self.limit:
                    break

        # self._set_skillcorner_attacking_directions(frames, periods)

        # frame_rate = 10

        # orientation = (
        #     Orientation.HOME_TEAM
        #     if periods[1].attacking_direction == AttackingDirection.HOME_AWAY
        #     else Orientation.AWAY_TEAM
        # )

        # metadata = Metadata(
        #     teams=teams,
        #     periods=sorted(periods.values(), key=lambda p: p.id),
        #     pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
        #     score=Score(
        #         home=metadata["home_team_score"],
        #         away=metadata["away_team_score"],
        #     ),
        #     frame_rate=frame_rate,
        #     orientation=orientation,
        #     provider=Provider.SKILLCORNER,
        #     flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
        #     coordinate_system=transformer.get_to_coordinate_system(),
        # )

        # return TrackingDataset(
        #     records=frames,
        #     metadata=metadata,
        # )
