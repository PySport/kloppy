from dataclasses import dataclass
from typing import List, Dict

from .common import Dataset, DataRecord
from .pitch import Point


@dataclass
class Frame(DataRecord):
    frame_id: int
    home_team_player_positions: Dict[str, Point]
    away_team_player_positions: Dict[str, Point]
    ball_position: Point


@dataclass
class TrackingDataset(Dataset):
    frame_rate: int
    records: List[Frame]

    @property
    def frames(self):
        return self.records


__all__ = ["Frame", "TrackingDataset"]
