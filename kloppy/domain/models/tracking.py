from dataclasses import dataclass, field
from typing import List, Dict, Optional

from kloppy.domain.models.common import DatasetType

from .common import Dataset, DataRecord, Player
from .pitch import Point


@dataclass
class PlayerData:
    coordinates: Point
    distance: Optional[float] = None
    speed: Optional[float] = None
    other_data: Dict[Player, Dict] = field(default_factory=dict)


@dataclass
class Frame(DataRecord):
    frame_id: int
    players_data: Dict[Player, PlayerData]
    other_data: Dict
    ball_coordinates: Point

    @property
    def players_coordinates(self):
        return {
            player: player_data.coordinates
            for player, player_data in self.players_data.items()
        }


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


__all__ = ["Frame", "TrackingDataset", "PlayerData"]
