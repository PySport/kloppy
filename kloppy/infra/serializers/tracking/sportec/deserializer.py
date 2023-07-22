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
from ...event.sportec.deserializer import _sportec_metadata_from_xml_elm

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
        with performance_logging("load data", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())

        with performance_logging("parse data", logger=logger):
            sportec_metadata = _sportec_metadata_from_xml_elm(match_root)
            teams = sportec_metadata.teams
            periods = sportec_metadata.periods
            transformer = self.get_transformer(
                length=sportec_metadata.x_max, width=sportec_metadata.y_max
            )

        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY
            else Orientation.FIXED_AWAY_HOME
        )

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=sportec_metadata.score,
            frame_rate=sportec_metadata.fps,
            orientation=orientation,
            provider=Provider.SPORTEC,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return TrackingDataset(
            records=[],
            metadata=metadata,
        )

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
