import logging
from datetime import timedelta, datetime, timezone
import warnings
from typing import List, Dict, NamedTuple, IO, Optional, Union, Iterable
import json

from kloppy.domain import (
    AttackingDirection,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    Point,
    Point3D,
    Provider,
    Team,
    TrackingDataset,
    PlayerData,
    attacking_directions_from_multi_frames,
    DatasetTransformer,
    BallState,
)
from kloppy.domain.services.frame_factory import create_frame
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.io import FileLike, open_as_file
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)


class SignalityInputs(NamedTuple):
    meta_data: IO[bytes]
    venue_information: IO[bytes]
    raw_data_feeds: Iterable[FileLike]


class SignalityDeserializer(TrackingDataDeserializer[SignalityInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
    ):
        super().__init__(limit, sample_rate, coordinate_system)

    @property
    def provider(self) -> Provider:
        return Provider.SIGNALITY

    @classmethod
    def _get_frame_data(
        cls,
        teams: List[Team],
        period: Period,
        frame: Dict,
        frame_id_offset: int,
    ):
        frame_id = frame_id_offset + frame["idx"]
        frame_timestamp = timedelta(milliseconds=frame["match_time"])

        ball_position = frame["ball"]["position"]
        if ball_position:
            ball_coordinates = Point3D(
                x=ball_position[0], y=ball_position[1], z=ball_position[2]
            )
        else:
            ball_coordinates = None

        players_data = {}
        for ix, side in enumerate(["home", "away"]):
            for raw_player_positional_info in frame[f"{side}_team"]:
                player = next(
                    (
                        player
                        for player in teams[ix].players
                        if player.jersey_no
                        == raw_player_positional_info["jersey_number"]
                    ),
                    None,
                )
                if player:
                    player_position = raw_player_positional_info["position"]
                    player_coordinates = Point(
                        x=player_position[0], y=player_position[1]
                    )
                    player_speed = raw_player_positional_info["speed"]
                    players_data[player] = PlayerData(
                        coordinates=player_coordinates, speed=player_speed
                    )
                else:
                    logger.debug(
                        f"Player with jersey no: {raw_player_positional_info['jersey_number']} not found in {side} team"
                    )

        ball_state = (
            BallState.ALIVE if frame["state"] == "running" else BallState.DEAD
        )
        if frame["ball"]["team"] == "home_team":
            ball_owning_team = teams[0]
        elif frame["ball"]["team"] == "away_team":
            ball_owning_team = teams[1]
        else:
            ball_owning_team = None

        return create_frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=ball_coordinates,
            players_data=players_data,
            period=period,
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            other_data={},
        )

    @classmethod
    def __create_teams(cls, metadata) -> List[Team]:
        teams = []
        for ground in [Ground.HOME, Ground.AWAY]:
            team = Team(
                team_id=metadata[f"team_{ground}_name"],
                name=metadata[f"team_{ground}_name"],
                ground=ground,
            )
            for player in metadata[f"team_{ground}_players"]:
                player = Player(
                    player_id=f"{ground}_{(player['jersey_number'])}",
                    name=player["name"],
                    team=team,
                    jersey_no=player["jersey_number"],
                )
                team.players.append(player)
            teams.append(team)

        return teams

    @classmethod
    def __get_frame_rate(cls, p1_tracking: List[Dict]) -> int:
        """gets the frame rate from the tracking data"""
        first_frame = p1_tracking[0]
        second_frame = p1_tracking[1]
        frame_rate = int(
            1
            / ((second_frame["match_time"] - first_frame["match_time"]) / 1000)
        )

        return frame_rate

    @classmethod
    def __get_periods(cls, raw_data_feeds) -> List[Period]:
        """gets the Periods contained in the tracking data"""
        periods = []
        for period_id, p_tracking in enumerate(raw_data_feeds, 1):
            first_frame = p_tracking[0]
            # compute the seconds since epoch
            start_ts = (
                first_frame["utc_time"] - first_frame["match_time"]
            ) / 1000
            # create an aware UTC datetime
            start_time = datetime.fromtimestamp(start_ts, tz=timezone.utc)

            last_frame = p_tracking[-1]
            assert (
                last_frame["state"] == "end"
            ), "Last frame must have state 'end'"
            # compute the seconds since epoch
            end_ts = (last_frame["utc_time"]) / 1000
            # create an aware UTC datetime
            end_time = datetime.fromtimestamp(end_ts, tz=timezone.utc)

            periods.append(
                Period(
                    id=period_id,
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                )
            )

        return periods

    def _load_frames(
        self,
        periods: List[Period],
        raw_data_feeds: List[List[Dict]],
        teams: List[Team],
        transformer: DatasetTransformer,
    ):
        p1_raw_data = raw_data_feeds[0]

        frames = []
        for period, p_raw_data in zip(periods, raw_data_feeds):
            n = 0
            sample = 1.0 / self.sample_rate
            if period.id == 1:
                frame_id_offset = 0
            elif period.id == 2:
                frame_id_offset = p1_raw_data[-1]["idx"] + 1
            else:
                raise ValueError(f"Period ID {period.id} not supported")

            for raw_frame in p_raw_data:
                if n % sample == 0:
                    frame = self._get_frame_data(
                        teams, period, raw_frame, frame_id_offset
                    )
                    if frame.players_data and frame.timestamp > timedelta(
                        seconds=0
                    ):
                        frame = transformer.transform_frame(frame)
                        frames.append(frame)
                n += 1
                if self.limit and n >= self.limit:
                    return frames

        return frames

    def deserialize(self, inputs: SignalityInputs) -> TrackingDataset:
        metadata = json.load(inputs.meta_data)
        venue_information = json.load(inputs.venue_information)
        raw_data_feeds = []
        for input_raw_data_feed in inputs.raw_data_feeds:
            with open_as_file(input_raw_data_feed) as raw_data_feed_fp:
                raw_data_feed = json.load(raw_data_feed_fp)
                raw_data_feeds.append(raw_data_feed)
        p1_raw_data = raw_data_feeds[0]

        with performance_logging("Loading metadata", logger=logger):
            frame_rate = self.__get_frame_rate(p1_raw_data)
            teams = self.__create_teams(metadata)
            periods = self.__get_periods(raw_data_feeds)
            pitch_size_length = venue_information["pitch_size"][0]
            pitch_size_width = venue_information["pitch_size"][1]

        transformer = self.get_transformer(
            pitch_length=pitch_size_length, pitch_width=pitch_size_width
        )

        with performance_logging("Loading data", logger=logger):
            frames = self._load_frames(
                periods, raw_data_feeds, teams, transformer
            )

        attacking_directions = attacking_directions_from_multi_frames(
            frames, periods
        )
        if attacking_directions[1] == AttackingDirection.LTR:
            orientation = Orientation.HOME_AWAY
        elif attacking_directions[1] == AttackingDirection.RTL:
            orientation = Orientation.AWAY_HOME
        else:
            warnings.warn(
                "Could not determine orientation of dataset, defaulting to NOT_SET"
            )
            orientation = Orientation.NOT_SET

        metadata = Metadata(
            teams=teams,
            periods=periods,
            frame_rate=frame_rate,
            orientation=orientation,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            coordinate_system=transformer.get_to_coordinate_system(),
            flags=None,
            provider=Provider.SIGNALITY,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
