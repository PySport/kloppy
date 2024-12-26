from dataclasses import dataclass, field
from math import isnan
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from kloppy.domain.models.common import DatasetType
from kloppy.utils import deprecated

from .common import DataRecord, Dataset, Official, Player
from .pitch import Point

TrackedObject = Union[Literal["ball"], Player, Official]


@dataclass
class TrackedObjectState:
    """
    The state of a trackable object in a frame.

    Attributes:
        coordinates: The coordinates of the object.
        distance: The distance the object has traveled since the previous frame.
        speed: The speed of the object.
        acceleration: The acceleration of the object.
        other_data: Additional data about the object.
    """

    coordinates: Point
    distance: Optional[float] = None
    speed: Optional[float] = None
    acceleration: Optional[float] = None
    other_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    """
    Detections of a trackable object over a sequence of consecutive frames.

    Attributes:
        tracked_object: The object being tracked. Either a player, official or "ball".
        start_frame: The frame of the first detection in the trajectory.
        end_frame: The frame of the last detection in the trajectory.
        detections: A list of [`Detection`][kloppy.domain.Detection] objects,
            one for each frame in the trajectory.
    """

    tracked_object: TrackedObject
    start_frame: "Frame"
    end_frame: "Frame"
    detections: List[TrackedObjectState]

    def __iter__(self):
        return iter(self.detections)

    def __len__(self):
        return len(self.detections)


@dataclass(repr=False)
class Frame(DataRecord):
    """
    A tracking data frame.

    Attributes:
        frame_id: The unique identifier of the frame. Aias for `record_id`.
        tracked_objects: A dictionary containing the tracking data for each object.
        ball_ball: The tracking data for the ball.
        ball_coordinates: The coordinates of the ball. Alias for `ball_data.coordinates`.
        ball_speed: The speed of the ball. Alias for `ball_data.speed`.
        players_data: A dictionary containing the tracking data for each player.
        players_coordinates: A dictionary containing the coordinates of each player.
        other_data: A dictionary containing additional data.
    """

    frame_id: int
    tracked_objects: Dict[TrackedObject, TrackedObjectState]
    other_data: Dict[str, Any]

    @property
    def record_id(self) -> int:
        return self.frame_id

    @property
    def ball_data(self) -> Optional[TrackedObjectState]:
        return self.tracked_objects.get("ball")

    @property
    def players_data(self) -> Dict[Player, TrackedObjectState]:
        return {
            player: state
            for player, state in self.tracked_objects.items()
            if isinstance(player, Player)
        }

    @property
    def ball_coordinates(self):
        if self.ball_data is None:
            return None
        return self.ball_data.coordinates

    @property
    def ball_speed(self):
        if self.ball_data is None:
            return None
        return self.ball_data.speed

    @property
    def players_coordinates(self):
        return {
            player: player_data.coordinates
            for player, player_data in self.players_data.items()
        }

    def __getitem__(self, object_id: Union[str, Player]):
        """Get the data for a specific object in the frame.

        Args:
            object_id: The ID of the object to get data for. Either a `Player`, player ID or "ball".
        Returns:
            The data for the object or `None` if the object is not in the frame.
        """
        if object_id == "ball":
            return self.ball_data
        if isinstance(object_id, Player):
            return self.players_data.get(object_id, None)
        for player in self.players_data.keys():
            if player.player_id == object_id:
                return self.players_data[player]
        return None


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

    def trajectories(self, tracked_object: TrackedObject):
        """Get trajectories for a specific object.

        A trajectory is a continuous track of the locations of a single player
        or the ball. A new trajectory starts every time a frame is missing or
        a player/ball is not tracked in a frame.

        Args:
            tracked_object: The object to get trajectories for. Either a player or "ball".

        Returns:
            A list of Trajectory objects.
        """
        trajectories = []
        current_trajectory = None
        for frame in self.records:
            state = frame[tracked_object]
            if (
                state is not None
                and state.coordinates is not None
                and not isnan(state.coordinates.x)
                and not isnan(state.coordinates.y)
            ):
                # The object is tracked in this frame
                if current_trajectory is None:
                    # but it was not tracked in the previous frame --> start
                    # a new trajectory
                    current_trajectory = Trajectory(
                        tracked_object=tracked_object,
                        start_frame=frame,
                        end_frame=frame,
                        detections=[state],
                    )
                elif (
                    frame.prev_record is not None
                    and frame.prev_record.record_id
                    == current_trajectory.end_frame.frame_id
                    and frame.prev_record.period.id == frame.period.id
                ):
                    # and it was tracked in the previous frame --> extend the
                    # current trajectory
                    current_trajectory.end_frame = frame
                    current_trajectory.detections.append(state)
                else:
                    # but a frame is missing or a new period started --> finish
                    # the current trajectory and start a new one
                    trajectories.append(current_trajectory)
                    current_trajectory = Trajectory(
                        tracked_object=tracked_object,
                        start_frame=frame,
                        end_frame=frame,
                        detections=[state],
                    )
            else:
                # The object is not tracked in this frame --> finish the
                # current trajectory
                if current_trajectory:
                    trajectories.append(current_trajectory)
                    current_trajectory = None
        # Finish the last trajectory
        if current_trajectory:
            trajectories.append(current_trajectory)
        return trajectories

    @deprecated(
        "to_pandas will be removed in the future. Please use to_df instead."
    )
    def to_pandas(
        self,
        record_converter: Optional[Callable[[Frame], Dict]] = None,
        additional_columns: Optional[
            Dict[str, Union[Callable[[Frame], Any], Any]]
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


__all__ = ["Frame", "TrackingDataset", "TrackedObjectState", "Trajectory"]
