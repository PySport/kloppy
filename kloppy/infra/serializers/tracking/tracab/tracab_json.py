import logging
import warnings
import json
import html
from datetime import timedelta
from typing import Dict, Optional, Union, Literal

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
    Metadata,
    Ground,
    Player,
    Provider,
    PlayerData,
    attacking_direction_from_frame,
)
from kloppy.domain.models import PositionType
from kloppy.exceptions import DeserializationError

from kloppy.utils import Readable, performance_logging

from .common import TRACABInputs, position_types_mapping
from .helpers import load_meta_data
from ..deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class TRACABJSONDeserializer(TrackingDataDeserializer[TRACABInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = True,
        meta_data_extension: Literal[".xml", ".json"] = None,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive
        self.meta_data_extension = meta_data_extension

    @property
    def provider(self) -> Provider:
        return Provider.TRACAB

    @classmethod
    def _create_frame(cls, teams, period, raw_frame, frame_rate):
        frame_id = raw_frame["FrameCount"]
        raw_players_data = raw_frame["PlayerPositions"]
        raw_ball_position = raw_frame["BallPosition"][0]

        players_data = {}
        for player_data in raw_players_data:
            if player_data["Team"] == 1:
                team = teams[0]
            elif player_data["Team"] == 0:
                team = teams[1]
            elif player_data["Team"] in (-1, 3, 4):
                continue
            else:
                raise DeserializationError(
                    f"Unknown Player Team ID: {player_data['Team']}"
                )

            jersey_no = player_data["JerseyNumber"]
            x = player_data["X"]
            y = player_data["Y"]
            speed = player_data["Speed"]

            player = team.get_player_by_jersey_number(jersey_no)
            if player:
                players_data[player] = PlayerData(
                    coordinates=Point(x, y), speed=speed
                )
            else:
                # continue
                raise DeserializationError(
                    f"Player not found for player jersey no {jersey_no} of team: {team.name}"
                )

        ball_x = raw_ball_position["X"]
        ball_y = raw_ball_position["Y"]
        ball_z = raw_ball_position["Z"]
        ball_speed = raw_ball_position["Speed"]
        if raw_ball_position["BallOwningTeam"] == "H":
            ball_owning_team = teams[0]
        elif raw_ball_position["BallOwningTeam"] == "A":
            ball_owning_team = teams[1]
        else:
            raise DeserializationError(
                f"Unknown ball owning team: {raw_ball_position['BallOwningTeam']}"
            )
        if raw_ball_position["BallStatus"] == "Alive":
            ball_state = BallState.ALIVE
        elif raw_ball_position["BallStatus"] == "Dead":
            ball_state = BallState.DEAD
        else:
            raise DeserializationError(
                f"Unknown ball state: {raw_ball_position['BallStatus']}"
            )

        return Frame(
            frame_id=frame_id,
            timestamp=timedelta(seconds=frame_id / frame_rate)
            - period.start_timestamp,
            ball_coordinates=Point3D(ball_x, ball_y, ball_z),
            ball_state=ball_state,
            ball_owning_team=ball_owning_team,
            ball_speed=ball_speed,
            players_data=players_data,
            period=period,
            other_data={},
        )

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "metadata" not in inputs:
            raise ValueError("Please specify a value for 'metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    def deserialize(self, inputs: TRACABInputs) -> TrackingDataset:
        (
            pitch_size_length,
            pitch_size_width,
            teams,
            periods,
            frame_rate,
            date,
            game_id,
        ) = load_meta_data(self.meta_data_extension, inputs.meta_data)
        raw_data = json.load(inputs.raw_data)

        transformer = self.get_transformer(
            pitch_length=pitch_size_length, pitch_width=pitch_size_width
        )

        with performance_logging("Loading data", logger=logger):
            raw_data = raw_data["FrameData"]

            def _iter():
                n = 0
                sample = 1.0 / self.sample_rate

                for frame in raw_data:
                    if (
                        self.only_alive
                        and frame["BallPosition"][0]["BallStatus"] == "Dead"
                    ):
                        continue

                    frame_id = frame["FrameCount"]
                    for _period in periods:
                        if (
                            _period.start_timestamp
                            <= timedelta(seconds=frame_id / frame_rate)
                            <= _period.end_timestamp
                        ):
                            if n % sample == 0:
                                yield _period, frame
                            n += 1

            frames = []
            for n, (_period, _frame) in enumerate(_iter()):
                frame = self._create_frame(teams, _period, _frame, frame_rate)

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

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=None,
            frame_rate=frame_rate,
            orientation=orientation,
            provider=Provider.TRACAB,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
            date=date,
            game_id=game_id,
        )

        return TrackingDataset(
            records=frames,
            metadata=metadata,
        )
