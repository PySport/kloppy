from dataclasses import dataclass, field
from typing import Any, Optional

from kloppy.domain.models.common import DatasetType
from kloppy.utils import (
    docstring_inherit_attributes,
)

from .common import DataRecord, Dataset, Player
from .pitch import Point, Point3D


@dataclass
class PlayerData:
    coordinates: Point
    distance: Optional[float] = None
    speed: Optional[float] = None
    other_data: dict[str, Any] = field(default_factory=dict)


@docstring_inherit_attributes(DataRecord)
@dataclass(repr=False)
class Frame(DataRecord):
    """
    Tracking data frame.

    Attributes:
        frame_id: The unique identifier of the frame. Aias for `record_id`.
        ball_coordinates: The coordinates of the ball
        players_data: A dictionary containing the tracking data for each player.
        ball_speed: The speed of the ball
        other_data: A dictionary containing additional data
    """

    frame_id: int
    players_data: dict[Player, PlayerData]
    other_data: dict[str, Any]
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

    def __str__(self):
        return f"<{self.__class__.__name__} frame_id='{self.frame_id}' time='{self.time}'>"

    def __repr__(self):
        return str(self)


@dataclass
@docstring_inherit_attributes(Dataset)
class TrackingDataset(Dataset[Frame]):
    """
    A tracking dataset.

    Attributes:
        dataset_type (DatasetType): `"DatasetType.TRACKING"`
        frames (List[Frame]): A list of frames. Alias for `records`.
        frame_rate (float): The frame rate (in Hertz) at which the data was recorded.
        metadata (Metadata): Metadata of the tracking dataset.
    """

    dataset_type: DatasetType = DatasetType.TRACKING

    @property
    def frames(self):
        return self.records

    @property
    def frame_rate(self):
        return self.metadata.frame_rate


__all__ = ["Frame", "TrackingDataset", "PlayerData"]
