from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Union, Any

from kloppy.domain.models.common import DatasetType

from .common import Dataset, DataRecord, Player
from .pitch import Point, Point3D


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

            def record_converter(frame: Frame) -> Dict:
                row = dict(
                    period_id=frame.period.id if frame.period else None,
                    timestamp=frame.timestamp,
                    ball_state=frame.ball_state.value
                    if frame.ball_state
                    else None,
                    ball_owning_team_id=frame.ball_owning_team.team_id
                    if frame.ball_owning_team
                    else None,
                    ball_x=frame.ball_coordinates.x
                    if frame.ball_coordinates
                    else None,
                    ball_y=frame.ball_coordinates.y
                    if frame.ball_coordinates
                    else None,
                    ball_z=getattr(frame.ball_coordinates, "z", None)
                    if frame.ball_coordinates
                    else None,
                )
                for player, player_data in frame.players_data.items():

                    row.update(
                        {
                            f"{player.player_id}_x": player_data.coordinates.x
                            if player_data.coordinates
                            else None,
                            f"{player.player_id}_y": player_data.coordinates.y
                            if player_data.coordinates
                            else None,
                            f"{player.player_id}_d": player_data.distance,
                            f"{player.player_id}_s": player_data.speed,
                        }
                    )

                    if player_data.other_data:
                        for name, value in player_data.other_data.items():
                            row.update(
                                {
                                    f"{player.player_id}_{name}": value,
                                }
                            )

                if frame.other_data:
                    for name, value in frame.other_data.items():
                        row.update(
                            {
                                name: value,
                            }
                        )

                return row

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
