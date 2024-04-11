from math import ceil, isnan
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from kloppy.domain.models.common import DatasetType
from kloppy.domain.models.pitch import (
    DEFAULT_PITCH_LENGTH,
    DEFAULT_PITCH_WIDTH,
)
from kloppy.exceptions import KloppyError
from kloppy.utils import deprecated

from .common import DataRecord, Dataset, Player
from .pitch import Point

try:
    import numpy as np
    from scipy.signal import savgol_filter
except ImportError:
    savgol_filter = None
    np = None


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
    objects: Dict[Union[Literal["ball"], Player], Detection]
    other_data: Dict[str, Any]

    @property
    def record_id(self) -> int:
        return self.frame_id

    @property
    def ball_data(self) -> Optional[Detection]:
        return self.objects.get("ball")

    @property
    def players_data(self) -> Dict[Player, Detection]:
        return {
            player: detection
            for player, detection in self.objects.items()
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

    def trajectories(self, trackable_object: Union[Player, Literal["ball"]]):
        """Get trajectories for a specific object.

        A trajectory is a continuous track of the locations of a single player
        or the ball. A new trajectory starts every time a frame is missing or
        a player/ball is not tracked in a frame.

        Args:
            trackable_object: The object to get trajectories for. Either a player or "ball".

        Returns:
            A list of Trajectory objects.
        """
        trajectories = []
        current_trajectory = None
        for frame in self.records:
            if (
                trackable_object in frame.objects
                and frame.objects[trackable_object].coordinates is not None
                and not isnan(frame.objects[trackable_object].coordinates.x)
                and not isnan(frame.objects[trackable_object].coordinates.y)
            ):
                # The object is tracked in this frame
                if current_trajectory is None:
                    # but it was not tracked in the previous frame --> start
                    # a new trajectory
                    current_trajectory = Trajectory(
                        trackable_object=trackable_object,
                        start_frame=frame.frame_id,
                        end_frame=frame.frame_id,
                        detections=[frame.objects[trackable_object]],
                    )
                elif (
                    frame.prev_record is not None
                    and frame.prev_record.frame_id
                    == current_trajectory.end_frame
                    and frame.prev_record.period.id == frame.period.id
                ):
                    # and it was tracked in the previous frame --> extend the
                    # current trajectory
                    current_trajectory.end_frame = frame.frame_id
                    current_trajectory.detections.append(
                        frame.objects[trackable_object]
                    )
                else:
                    # but a frame is missing or a new period started --> finish
                    # the current trajectory and start a new one
                    trajectories.append(current_trajectory)
                    current_trajectory = Trajectory(
                        trackable_object=trackable_object,
                        start_frame=frame.frame_id,
                        end_frame=frame.frame_id,
                        detections=[frame.objects[trackable_object]],
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

    def compute_ball_kinematics(
        self,
        n_smooth_speed: int = 6,
        n_smooth_acc: int = 10,
        filter_type: Optional[
            Literal["savitzky_golay", "moving_average"]
        ] = "savitzky_golay",
        polyorder: int = 3,
        window_length: int = 31,
        max_speed: float = 50.0,
        copy: bool = True,
    ):
        """Compute speed and acceleration of the ball.

        Args:
            n_smooth_speed: The number of frames to smooth over when computing speed.
            n_smooth_acc: The number of frames to smooth over when computing acceleration.
            filter_type: The type of filter to use when smoothing. Either "savitzky_golay", "moving_average" or None.
            polyorder: Polyorder to use when the savitzky_golay filter is selected. Defaults to 3.
            window_length: Window length of the filter. Defaults to 31 frames.
            max_speed_player: The maximum speed allowed for a player (in m/s).
            max_speed_ball: The maximum speed allowed for the ball (in m/s).
            copy: If True, a new dataset is returned with the computed kinematics. If False, the dataset is modified in place.
        Returns:
            TrackingDataset: A new dataset with the computed kinematics.

        See Also:
            compute_player_kinematics
        """
        new_dataset = self._copy_detections() if copy else self
        new_dataset._add_kinematics(
            trackable_object="ball",
            n_smooth_speed=n_smooth_speed,
            n_smooth_acc=n_smooth_acc,
            filter_type=filter_type,
            polyorder=polyorder,
            window_length=window_length,
            max_speed=max_speed,
        )
        return new_dataset

    def compute_player_kinematics(
        self,
        n_smooth_speed: int = 6,
        n_smooth_acc: int = 10,
        filter_type: Optional[
            Literal["savitzky_golay", "moving_average"]
        ] = "savitzky_golay",
        polyorder: int = 3,
        window_length: int = 31,
        max_speed: float = 12.0,
        copy: bool = True,
    ):
        """Compute speed and acceleration for each player in the dataset.

        Args:
            n_smooth_speed: The number of frames to smooth over when computing speed.
            n_smooth_acc: The number of frames to smooth over when computing acceleration.
            filter_type: The type of filter to use when smoothing. Either "savitzky_golay", "moving_average" or None.
            polyorder: Polyorder to use when the savitzky_golay filter is selected. Defaults to 3.
            window_length: Window length of the filter. Defaults to 31 frames.
            max_speed_player: The maximum speed allowed for a player (in m/s).
            max_speed_ball: The maximum speed allowed for the ball (in m/s).
            copy: If True, a new dataset is returned with the computed kinematics. If False, the dataset is modified in place.
        Returns:
            TrackingDataset: A new dataset with the computed kinematics.

        See Also:
            compute_ball_kinematics
        """
        new_dataset = self._copy_detections() if copy else self
        for team in self.metadata.teams:
            for player in team.players:
                new_dataset._add_kinematics(
                    trackable_object=player,
                    n_smooth_speed=n_smooth_speed,
                    n_smooth_acc=n_smooth_acc,
                    filter_type=filter_type,
                    polyorder=polyorder,
                    window_length=window_length,
                    max_speed=max_speed,
                )
        return new_dataset

    def _copy_detections(self):
        """Create a copy of each detection in the tracking dataset."""
        return replace(
            self,
            records=[
                replace(
                    record,
                    objects={
                        trackable_object: replace(detection)
                        for trackable_object, detection in record.objects.items()
                    },
                )
                for record in self.records
            ],
        )

    def _add_kinematics(
        self,
        trackable_object: Union[Player, Literal["ball"]],
        n_smooth_speed: int,
        n_smooth_acc: int,
        filter_type: Optional[Literal["savitzky_golay", "moving_average"]],
        polyorder: int,
        window_length: int,
        max_speed: float,
    ) -> None:
        """Add speed and acceleration to each each detection of an object in the dataset.

        Args:
            trackable_object: The object to compute kinematics for. Either a player or "ball".
            n_smooth_speed: The number of frames to smooth over when computing speed.
            n_smooth_acc: The number of frames to smooth over when computing acceleration.
            filter_type: The type of filter to use when smoothing. Either "savitzky_golay", "moving_average" or None.
            polyorder: Polyorder to use when the savitzky_golay filter is selected. Defaults to 3.
            window_length: Window length of the filter. Defaults to 31 frames.
            max_speed_player: The maximum speed allowed for a player (in m/s).
            max_speed_ball: The maximum speed allowed for the ball (in m/s).
        """
        if np is None:
            raise ImportError(
                "Numpy is required to compute kinematics. Please install it using: pip install numpy"
            )

        if self.metadata.frame_rate is None:
            raise KloppyError(
                "Frame rate is not set in metadata. Please set the frame rate before computing kinematics."
            )

        n_smooth_speed = 1 if n_smooth_speed < 1 else n_smooth_speed
        n_smooth_acc = 1 if n_smooth_acc < 1 else n_smooth_acc

        for trajectory in self.trajectories(trackable_object):
            if len(trajectory) < n_smooth_speed + 1:
                for i, detection in enumerate(trajectory):
                    detection.distance = np.nan
                    detection.speed = np.nan
                    detection.acceleration = np.nan
                continue

            # get x-y coordinates in metric space
            tracked_maps = np.empty((len(trajectory), 2))
            for i, detection in enumerate(trajectory):
                point = detection.coordinates
                metric_point = self.metadata.pitch_dimensions.to_metric_base(
                    point,
                    pitch_length=self.metadata.pitch_dimensions.pitch_length
                    or DEFAULT_PITCH_LENGTH,
                    pitch_width=self.metadata.pitch_dimensions.pitch_width
                    or DEFAULT_PITCH_WIDTH,
                )
                tracked_maps[i] = [metric_point.x, metric_point.y]

            # apply a filter for smoothing
            if filter_type == "savitzky_golay":
                tracked_maps = _apply_savgol_filter(
                    tracked_maps, polyorder, window_length
                )
            elif filter_type == "moving_average":
                tracked_maps = _apply_savgol_filter(
                    tracked_maps, 0, window_length
                )
            elif filter_type is not None:
                raise ValueError(
                    f"Unknown filter type: {filter_type}. Supported types are 'savitzky_golay' and 'moving_average'."
                )

            # get speed vect and speed norm
            dist = (
                tracked_maps[n_smooth_speed:] - tracked_maps[:-n_smooth_speed]
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
                acc_vect = diff_acc / (n_smooth_acc / self.metadata.frame_rate)

                # padding to respect the shape after the smoothing
                add_acc_before = np.zeros((ceil(n_smooth_acc / 2), 2)) + np.nan
                add_acc_after = np.zeros((n_smooth_acc // 2, 2)) + np.nan
                acc_vect = np.concatenate(
                    (add_acc_before, acc_vect, add_acc_after)
                )

                # apply a physical check based on speed and acc
                acc_vect = _apply_criterion(speed_vect, acc_vect, max_speed)

                # acc norm process for other tracks
                diff_acc = (
                    speed_norm[n_smooth_acc:] - speed_norm[:-n_smooth_acc]
                )
                acc_norm = diff_acc / (n_smooth_acc / self.metadata.frame_rate)

                # padding to respect the shape after the smoothing
                add_acc_norm_before = (
                    np.zeros((ceil(n_smooth_acc / 2))) + np.nan
                )
                add_acc_norm_after = np.zeros((n_smooth_acc // 2)) + np.nan
                acc_norm = np.concatenate(
                    (add_acc_norm_before, acc_norm, add_acc_norm_after)
                )

            # apply last padding
            add_speed_before = np.zeros((ceil(n_smooth_speed / 2), 2)) + np.nan
            add_speed_after = np.zeros((n_smooth_speed // 2, 2)) + np.nan
            speed_vect = np.concatenate(
                (add_speed_before, speed_vect, add_speed_after)
            )

            add_speed_norm_before = (
                np.zeros((ceil(n_smooth_speed / 2))) + np.nan
            )
            add_speed_norm_after = np.zeros((n_smooth_speed // 2)) + np.nan
            dist_norm = np.concatenate(
                (add_speed_norm_before, dist_norm, add_speed_norm_after)
            )
            speed_norm = np.concatenate(
                (add_speed_norm_before, speed_norm, add_speed_norm_after)
            )
            acc_norm = np.concatenate(
                (add_speed_norm_before, acc_norm, add_speed_norm_after)
            )

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


def _apply_criterion(speeds, acc, max_speed):
    """Criterion used to spot tracking inaccuracies.

    Args:
        speeds (np.array): one player/ball speed (vx, vy) per row
        acc (np.array): one player/ball acceleration (ax, ay) per row, same shape as speeds
        max_speed (float): maximum speed allowed for a player or the ball

    Returns:
        acc: same as acc with value set to np.NaN if criterion <= 0
    """
    assert np is not None
    criterion = -(9.1 / max_speed) * speeds + 9.1 - acc
    mask = np.isnan(criterion)
    criterion[mask] = -np.inf
    mask_criterion = criterion <= 0.0
    acc[mask_criterion] = np.nan
    return acc


def _apply_savgol_filter(raw_maps, polyorder, window_length):
    """Smooth player/ball positions using a Savitzky-Golay filter.

    Args:
        raw_maps (np.array): one player/ball position (x, y) per row

    Returns:
        tracked_maps: smoothed player positions
    """
    if savgol_filter is None:
        raise ImportError(
            "Scipy is required to apply a Savitzky-Golay smoothing filter. "
            "Please install it using: pip install scipy"
        )

    window_length = min(raw_maps.shape[0], window_length)
    if window_length % 2 == 0:
        window_length = window_length - 1
    polyorder = min(window_length - 1, 1)
    tracked_maps = savgol_filter(raw_maps, window_length, polyorder, axis=0)
    return tracked_maps


__all__ = ["Frame", "TrackingDataset", "Detection", "Trajectory"]
