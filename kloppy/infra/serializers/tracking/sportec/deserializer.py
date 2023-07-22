import json
import logging
from typing import Tuple, Dict, NamedTuple, Optional, Union, IO

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
    Provider,
    Orientation,
    attacking_direction_from_frame,
    Metadata,
    Ground,
    Player,
    build_coordinate_system,
    Provider,
    PlayerData,
)

from kloppy.utils import Readable, performance_logging

from ..deserializer import TrackingDataDeserializer

logger = logging.getLogger(__name__)


class SportecTrackingDataInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class SportecTrackingDataSerializer(TrackingDataDeserializer):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: Optional[bool] = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    def deserialize(
        self, inputs: SportecTrackingDataInputs
    ) -> TrackingDataset:
        return TrackingDataset(
            records=[],
            metadata=None,
        )

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
