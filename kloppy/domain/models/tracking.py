from dataclasses import dataclass
from typing import List, Dict

from .common import Dataset, DataRecord
from .pitch import Point


@dataclass
class Frame(DataRecord):
    frame_id: int
    players_positions: Dict[str, Point]
    ball_position: Point


@dataclass
class TrackingDataset(Dataset):
    records: List[Frame]

    @property
    def frames(self):
        return self.records


__all__ = ["Frame", "TrackingDataset"]
