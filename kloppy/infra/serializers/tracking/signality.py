import logging
from datetime import timedelta, datetime
import warnings
from typing import List, Dict, Tuple, NamedTuple, IO, Optional, Union
from enum import Enum, Flag
from collections import Counter
import numpy as np
import json
from pathlib import Path

from kloppy.domain import (
    attacking_direction_from_frame,
    AttackingDirection,
    DatasetFlag,
    Frame,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    Point,
    Point3D,
    Position,
    Provider,
    Score,
    Team,
    TrackingDataset,
    PlayerData,
    MetricPitchDimensions,
    Dimension,
    CoordinateSystem,
)
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)


class SignalityInputs(NamedTuple):
    meta_data: IO[bytes]
    venue_information: IO[bytes]
    p1_raw_data: IO[bytes]
    p2_raw_data: IO[bytes]


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

        return Frame(
            frame_id=frame_id,
            timestamp=frame_timestamp,
            ball_coordinates=ball_coordinates,
            players_data=players_data,
            period=period,
            ball_state=None,
            ball_owning_team=None,
            other_data={},
        )

    @classmethod
    def _get_signality_attacking_directions(
        cls, frames: List[Frame], periods: List[Period]
    ) -> Dict[int, AttackingDirection]:
        """
        with only partial tracking data we cannot rely on a single frame to
        infer the attacking directions as a simple average of only some players
        x-coords might not reflect the attacking direction.
        """
        attacking_directions = {}
        frame_period_ids = np.array([_frame.period.id for _frame in frames])
        frame_attacking_directions = np.array(
            [
                attacking_direction_from_frame(frame)
                if len(frame.players_data) > 0
                else AttackingDirection.NOT_SET
                for frame in frames
            ]
        )

        for period in periods:
            period_id = period.id
            if period_id in frame_period_ids:
                count = Counter(
                    frame_attacking_directions[frame_period_ids == period_id]
                )
                attacking_directions[period_id] = count.most_common()[0][0]
            else:
                attacking_directions[period_id] = AttackingDirection.NOT_SET

        return attacking_directions

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
    def __get_periods(cls, p1_tracking, p2_tracking) -> List[Period]:
        """gets the Periods contained in the tracking data"""
        periods = []
        for period_id, p_tracking in enumerate([p1_tracking, p2_tracking], 1):
            first_frame = p_tracking[0]
            start_time = datetime.utcfromtimestamp(
                (first_frame["utc_time"] - first_frame["match_time"]) / 1000
            )

            last_frame = p_tracking[-1]
            assert (
                last_frame["state"] == "end"
            ), "Last frame must have state 'end'"
            end_time = datetime.utcfromtimestamp(last_frame["utc_time"] / 1000)

            periods.append(
                Period(
                    id=period_id,
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                )
            )

        return periods

    def deserialize(self, inputs: SignalityInputs) -> TrackingDataset:
        metadata = json.load(inputs.meta_data)
        venue_information = json.load(inputs.venue_information)
        p1_raw_data = json.load(inputs.p1_raw_data)
        p2_raw_data = json.load(inputs.p2_raw_data)

        with performance_logging("Loading metadata", logger=logger):
            frame_rate = self.__get_frame_rate(p1_raw_data)
            teams = self.__create_teams(metadata)
            periods = self.__get_periods(p1_raw_data, p2_raw_data)
            pitch_size_length = venue_information["pitch_size"][0]
            pitch_size_width = venue_information["pitch_size"][1]

        transformer = self.get_transformer(
            pitch_length=pitch_size_length, pitch_width=pitch_size_width
        )

        with performance_logging("Loading data", logger=logger):
            frames = []
            for period, p_raw_data in zip(periods, [p1_raw_data, p2_raw_data]):
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

        attacking_directions = self._get_signality_attacking_directions(
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
