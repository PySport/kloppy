from typing import Optional, Iterable, Callable

from kloppy.domain import TrackingDataset, Frame, Player
from kloppy.infra.serializers.tracking.hawkeye import (
    HawkEyeDeserializer,
    HawkEyeInputs,
)
from kloppy.io import FileLike, _check_path_type


def load(
    ball_feeds: Iterable[FileLike],
    player_centroid_feeds: Iterable[FileLike],
    meta_data: Optional[FileLike] = None,
    pitch_width: Optional[float] = 68.0,
    pitch_length: Optional[float] = 105.0,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    show_progress: Optional[bool] = False,
) -> TrackingDataset:

    ball_feeds = _check_path_type(ball_feeds, contains="samples.ball")
    player_centroid_feeds = _check_path_type(
        player_centroid_feeds, contains="samples.centroids"
    )

    deserializer = HawkEyeDeserializer(
        pitch_width=pitch_width,
        pitch_length=pitch_length,
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
    )
    return deserializer.deserialize(
        inputs=HawkEyeInputs(
            ball_feeds=ball_feeds,
            player_centroid_feeds=player_centroid_feeds,
            meta_data=meta_data,
            show_progress=show_progress,
        )
    )
