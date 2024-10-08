from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Union, Any

from kloppy.domain.models.common import DatasetType

from .common import Dataset, DataRecord, Player
from .pitch import Point, Point3D
from kloppy.utils import (
    deprecated,
)


@dataclass
class PlayerData:
    coordinates: Point
    distance: Optional[float] = None
    speed: Optional[float] = None
    other_data: Dict[str, Any] = field(default_factory=dict)


@dataclass(repr=False)
class Frame(DataRecord):
    frame_id: int
    players_data: Dict[Player, PlayerData]
    other_data: Dict[str, Any]
    ball_coordinates: Point3D
    ball_speed: Optional[float] = None

    @property
    def record_id(self) -> int:
        return self.frame_id

    @property
    def players_coordinates(self):
        return {
            player: player_data.coordinates
            for player, player_data in self.players_data.items()
        }


@dataclass
class TrackingDataset(Dataset[Frame]):
    records: List[Frame]

    dataset_type: DatasetType = DatasetType.TRACKING

    @property
    def frames(self):
        return self.records

    @property
    def frame_rate(self):
        return self.metadata.frame_rate

    @deprecated(
        "to_pandas will be removed in the future. Please use to_df instead."
    )
    def to_pandas(
        self,
        record_converter: Callable[[Frame], Dict] = None,
        additional_columns: Dict[
            str, Union[Callable[[Frame], Any], Any]
        ] = None,
    ) -> "DataFrame":
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Seems like you don't have pandas installed. Please"
                " install it using: pip install pandas"
            )

        if not record_converter:
            from ..services.transformers.attribute import (
                DefaultFrameTransformer,
            )

            record_converter = DefaultFrameTransformer()

        def generic_record_converter(frame: Frame):
            row = record_converter(frame)
            if additional_columns:
                for k, v in additional_columns.items():
                    if callable(v):
                        value = v(frame)
                    else:
                        value = v
                    row.update({k: value})

            return row

        return pd.DataFrame.from_records(
            map(generic_record_converter, self.records)
        )


__all__ = ["Frame", "TrackingDataset", "PlayerData"]
