from dataclasses import dataclass
from typing import List, Dict

from .common import Dataset, DataRecord, Ground
from .pitch import Point


@dataclass
class Frame(DataRecord):
    frame_id: int
    players_coordinates: Dict[str, Point]
    players_ground: Dict[str, Ground]
    ball_position: Point

    @property
    def home_team_players_coordinates(self):
        return {
            player_id: coordinates
            for (player_id, coordinates) in self.players_coordinates.items()
            if self.players_ground[player_id] == Ground.HOME
        }

    @property
    def away_team_players_coordinates(self):
        return {
            player_id: coordinates
            for (player_id, coordinates) in self.players_coordinates.items()
            if self.players_ground[player_id] == Ground.AWAY
        }


@dataclass
class TrackingDataset(Dataset):
    records: List[Frame]

    @property
    def frames(self):
        return self.records

    @property
    def frame_rate(self):
        return self.meta_data.frame_rate


__all__ = ["Frame", "TrackingDataset"]
