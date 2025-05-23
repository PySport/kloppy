import logging
import warnings
from typing import IO, NamedTuple, Optional, Union

from kloppy.domain import (
    AttackingDirection,
    DatasetFlag,
    Metadata,
    Orientation,
    Provider,
    TrackingDataset,
    attacking_direction_from_frame,
)
from kloppy.utils import performance_logging

from ..deserializer import TrackingDataDeserializer
from .parsers import get_metadata_parser, get_raw_data_parser

logger = logging.getLogger(__name__)


class TRACABInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class TRACABDeserializer(TrackingDataDeserializer[TRACABInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: bool = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    @property
    def provider(self) -> Provider:
        return Provider.TRACAB

    def deserialize(self, inputs: TRACABInputs) -> TrackingDataset:
        with performance_logging("Loading metadata", logger=logger):
            metadata_parser = get_metadata_parser(inputs.meta_data)
            (
                pitch_length,
                pitch_width,
            ) = metadata_parser.extract_pitch_dimensions()
            teams = metadata_parser.extract_lineups()
            periods = metadata_parser.extract_periods()
            frame_rate = metadata_parser.extract_frame_rate()
            date = metadata_parser.extract_date()
            game_id = metadata_parser.extract_game_id()
            orientation = metadata_parser.extract_orientation()

        transformer = self.get_transformer(
            pitch_length=pitch_length, pitch_width=pitch_width
        )

        with performance_logging("Loading data", logger=logger):
            raw_data_parser = get_raw_data_parser(
                inputs.raw_data, periods, teams, frame_rate
            )
            frames = []
            for n, frame in enumerate(
                raw_data_parser.extract_frames(
                    self.sample_rate, self.only_alive
                )
            ):
                frame = transformer.transform_frame(frame)
                frames.append(frame)

                if self.limit and n + 1 >= (self.limit / self.sample_rate):
                    break

        if orientation is None:
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
            teams=list(teams),
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
