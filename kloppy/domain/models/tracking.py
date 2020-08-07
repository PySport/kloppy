from dataclasses import dataclass
from typing import List, Dict

from kloppy.domain.models.common import DatasetType

from .common import Dataset, DataRecord, Player
from .pitch import Point


@dataclass
class Frame(DataRecord):
    frame_id: int
    players_coordinates: Dict[Player, Point]
    ball_coordinates: Point


@dataclass
class TrackingDataset(Dataset):
    records: List[Frame]

    dataset_type: DatasetType = DatasetType.TRACKING

    @property
    def frames(self):
        return self.records

    @property
    def frame_rate(self):
        return self.metadata.frame_rate


__all__ = ["Frame", "TrackingDataset"]
