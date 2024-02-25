from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
from scipy.signal import savgol_filter

from kloppy.domain.models.common import DatasetType
from kloppy.exceptions import KloppyError
from kloppy.utils import deprecated

from .common import DataRecord, Dataset, Player
from .pitch import Point


@dataclass
class Detection:
    """A single detection of a trackable object in a frame.

    Attributes:
        coordinates: The coordinates of the object in the frame.
        distance: The distance the object has traveled since the previous frame.
        speed: The speed of the object in the frame.
        acceleration: The acceleration of the object in the frame.
        other_data: Additional data about the object in the frame.
    """

    coordinates: Point
    distance: Optional[float] = None
    speed: Optional[float] = None
    acceleration: Optional[float] = None
    other_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    """Detections of a trackable object over a sequence of consecutive frames.

    Attributes:
        trackable_object: The object being tracked. Either a player or "ball".
        start_frame: The frame number of the first detection in the trajectory.
        end_frame: The frame number of the last detection in the trajectory.
        detections: A list of Detection objects, one for each frame in the trajectory.
    """

    trackable_object: Union[Player, str]
    start_frame: int
    end_frame: int
    detections: List[Detection]

    def __iter__(self):
        return iter(self.detections)

    def __len__(self):
        return len(self.detections)


@dataclass(repr=False)
class Frame(DataRecord):
    frame_id: int
    ball_data: Optional[Detection]
    players_data: Dict[Player, Detection]
    other_data: Dict[str, Any]

    @property
    def record_id(self) -> int:
        return self.frame_id

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

    @property
    def trajectories(self):
        trajectories = defaultdict(list)

        # get ball trajectories
        current_trajectory = None
        for record in self.records:
            if (
                record.ball_data
                and record.ball_data.coordinates
                and record.ball_data.coordinates.x != float("nan")
            ):
                if current_trajectory is None:
                    current_trajectory = Trajectory(
                        trackable_object="ball",
                        start_frame=record.frame_id,
                        end_frame=record.frame_id,
                        detections=[record.ball_data],
                    )
                else:
                    current_trajectory.end_frame = record.frame_id
                    current_trajectory.detections.append(record.ball_data)
            else:
                if current_trajectory:
                    trajectories["ball"].append(current_trajectory)
                    current_trajectory = None
        if current_trajectory:
            trajectories["ball"].append(current_trajectory)

        # get player trajectories
        for team in self.metadata.teams:
            for player in team.players:
                current_trajectory = None
                for record in self.records:
                    if (
                        player in record.players_data
                        and record.players_data[player].coordinates is not None
                        and record.players_data[player].coordinates.x
                        != float("nan")
                    ):
                        if current_trajectory is None:
                            current_trajectory = Trajectory(
                                trackable_object=player,
                                start_frame=record.frame_id,
                                end_frame=record.frame_id,
                                detections=[record.players_data[player]],
                            )
                        else:
                            current_trajectory.end_frame = record.frame_id
                            current_trajectory.detections.append(
                                record.players_data[player]
                            )
                    else:
                        if current_trajectory:
                            trajectories[player].append(current_trajectory)
                            current_trajectory = None
                if current_trajectory:
                    trajectories[player].append(current_trajectory)

        return trajectories

    def compute_kinematics(
        self,
        n_smooth_speed: int = 6,
        n_smooth_acc: int = 10,
        max_speed_player: float = 12.0,
        max_speed_ball: float = 50.0,
    ):
        """Compute speed and acceleration for each object in the dataset.

        Args:
            n_smooth_speed: The number of frames to smooth over when computing speed.
            n_smooth_acc: The number of frames to smooth over when computing acceleration.
            max_speed_player: The maximum speed allowed for a player (in m/s).
            max_speed_ball: The maximum speed allowed for the ball (in m/s).

        """
        if self.metadata.frame_rate is None:
            raise KloppyError(
                "Frame rate is not set in metadata. Please set the frame rate before computing kinematics."
            )
        for trackable_object, trajectories in self.trajectories.items():
            max_speed = (
                max_speed_player
                if isinstance(trackable_object, Player)
                else max_speed_ball
            )

            for trajectory in trajectories:
                if len(trajectory) < n_smooth_speed + 1:
                    continue

                # get x-y coordinates in metric space
                tracked_maps = np.empty((len(trajectory), 2))
                for i, detection in enumerate(trajectory):
                    point = detection.coordinates
                    metric_point = self.metadata.pitch_dimensions.to_base(
                        point
                    )
                    tracked_maps[i] = [metric_point.x, metric_point.y]

                # apply a Savitzky-Golay filter for smoothing
                tracked_maps = smoothing_savgol_3rd(tracked_maps)

                # get speed vect and speed norm
                dist = (
                    tracked_maps[n_smooth_speed:]
                    - tracked_maps[:-n_smooth_speed]
                )
                dist_norm = np.linalg.norm(dist, axis=1) / n_smooth_speed

                speed_vect = dist / (n_smooth_speed / self.metadata.frame_rate)
                speed_norm = np.linalg.norm(speed_vect, axis=1)

                # acc process for short tracks
                if speed_vect.shape[0] < self.metadata.frame_rate:
                    acc_vect = np.nan * np.ones_like(speed_vect)
                    acc_norm = np.nan * np.ones_like(speed_norm)
                else:
                    # acc vect process for other tracks
                    diff_acc = (
                        speed_vect[n_smooth_acc:] - speed_vect[:-n_smooth_acc]
                    )
                    acc_vect = diff_acc / (
                        n_smooth_acc / self.metadata.frame_rate
                    )

                    # padding to respect the shape after the smoothing
                    add = np.zeros((n_smooth_acc // 2, 2)) + np.nan
                    acc_vect = np.concatenate((add, acc_vect, add))

                    # apply a physical check based on speed and acc
                    acc_vect = apply_criterion(speed_vect, acc_vect, max_speed)

                    # acc norm process for other tracks
                    diff_acc = (
                        speed_norm[n_smooth_acc:] - speed_norm[:-n_smooth_acc]
                    )
                    acc_norm = diff_acc / (
                        n_smooth_acc / self.metadata.frame_rate
                    )

                    # padding to respect the shape after the smoothing
                    add = np.zeros((n_smooth_acc // 2)) + np.nan
                    acc_norm = np.concatenate((add, acc_norm, add))

                # apply last padding
                add = np.zeros((n_smooth_speed // 2, 2)) + np.nan
                speed_vect = np.concatenate((add, speed_vect, add))

                add = np.zeros((n_smooth_speed // 2)) + np.nan
                dist_norm = np.concatenate((add, dist_norm, add))
                speed_norm = np.concatenate((add, speed_norm, add))
                acc_norm = np.concatenate((add, acc_norm, add))

                # fill detection dict with physical info
                for i, detection in enumerate(trajectory):
                    detection.distance = dist_norm[i]
                    detection.speed = speed_norm[i]
                    detection.acceleration = acc_norm[i]

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


def apply_criterion(speeds, acc, max_speed):
    """
    Criterion used to spot tracking inaccuracies.

    Args:
        speeds (np.array): one player/ball speed (vx, vy) per row
        acc (np.array): one player/ball acceleration (ax, ay) per row, same shape as speeds
        max_speed (float): maximum speed allowed for a player or the ball

    Returns:
        acc: same as acc with value set to np.NaN if criterion <= 0
    """
    criterion = -(9.1 / max_speed) * speeds + 9.1 - acc
    mask = np.isnan(criterion)
    criterion[mask] = -np.inf
    mask_criterion = criterion <= 0.0
    acc[mask_criterion] = np.nan
    return acc


def smoothing_savgol_3rd(raw_maps):
    """
    Smooth player/ball positions using a Savitzky-Golay filter.

    Args:
        raw_maps (np.array): one player/ball position (x, y) per row

    Returns:
        tracked_maps: smoothed player positions
    """
    window_length = min(raw_maps.shape[0], 31)
    if window_length % 2 == 0:
        window_length = window_length - 1
    polyorder = min(window_length - 1, 3)
    tracked_maps = savgol_filter(raw_maps, window_length, polyorder, axis=0)
    return tracked_maps


__all__ = ["Frame", "TrackingDataset", "Detection", "Trajectory"]
