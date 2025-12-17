import logging
from typing import IO, NamedTuple, Optional, Union

from kloppy.domain import (
    PositionType,
    Provider,
    TrackingDataset,
)
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)

logger = logging.getLogger(__name__)

FRAME_RATE = None

position_types_mapping: dict[int, PositionType] = {
    "LW": PositionType.LeftWing,
    "LCF": PositionType.LeftForward,
    "CF": PositionType.Striker,
    "RCF": PositionType.RightForward,
    "RW": PositionType.RightWing,
    "LAM": PositionType.LeftAttackingMidfield,
    "CAM": PositionType.CenterAttackingMidfield,
    "RAM": PositionType.RightAttackingMidfield,
    "LM": PositionType.LeftMidfield,
    "LCM": PositionType.LeftCentralMidfield,
    "CM": PositionType.CentralMidfield,
    "RCM": PositionType.RightCentralMidfield,
    "RM": PositionType.RightMidfield,
    "LDM": PositionType.LeftDefensiveMidfield,
    "CDM": PositionType.CenterDefensiveMidfield,
    "RDM": PositionType.RightDefensiveMidfield,
    "LB": PositionType.LeftBack,
    "LCB": PositionType.LeftCenterBack,
    "CB": PositionType.CenterBack,
    "RCB": PositionType.RightCenterBack,
    "RB": PositionType.RightBack,
    "GK": PositionType.Goalkeeper,
    "SUB": PositionType.Unknown,
}


class CDFTrackingDataInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class CDFTrackingDeserializer(TrackingDataDeserializer[CDFTrackingDataInputs]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        include_empty_frames: Optional[bool] = False,
        only_alive: bool = True,
    ):
        super().__init__(limit, sample_rate, coordinate_system)
        self.include_empty_frames = include_empty_frames
        self.only_alive = only_alive

    @property
    def provider(self) -> Provider:
        return Provider.CDF

    def deserialize(self, inputs: CDFTrackingDataInputs) -> TrackingDataset:
        print(inputs.meta_data)
