from dataclasses import dataclass
from typing import List, Dict

from .common import (
    DataSet,
    DataRecord
)
from .pitch import Point


@dataclass
class Frame(DataRecord):
    frame_id: int
    home_team_player_positions: Dict[str, Point]
    away_team_player_positions: Dict[str, Point]
    ball_position: Point


@dataclass
class TrackingDataSet(DataSet):
    frame_rate: int
    records: List[Frame]

    @property
    def frames(self):
        return self.records
