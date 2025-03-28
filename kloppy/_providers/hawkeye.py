from typing import Iterable, Optional, Union

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.hawkeye import (
    HawkEyeDeserializer,
    HawkEyeInputs,
)
from kloppy.io import FileLike, expand_inputs


def load(
    ball_feeds: Union[FileLike, Iterable[FileLike]],
    player_centroid_feeds: Union[FileLike, Iterable[FileLike]],
    meta_data: Optional[FileLike] = None,
    pitch_width: Optional[float] = 68.0,
    pitch_length: Optional[float] = 105.0,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    show_progress: Optional[bool] = False,
) -> TrackingDataset:
    """
    Load HawkEye tracking data.

    HawkEye splits up the data of a single game into multiple files, typically
    one file per minute. The `ball_feeds` and `player_centroid_feeds` arguments
    support various options on how to provide these files:

        - A file-like object to load the data for a single minute of the match.
        - An ordered list of file-like objects to load the data for multiple
          minutes of the match.
        - A directory containing the files to load. This requires that the ball
          feeds end with `.samples.ball` and the player centroid feeds end with
          `.samples.centroids`.


    Args:
        ball_feeds: The ball tracking data.
        player_centroid_feeds: The player centroid tracking data.
        meta_data: A json or xml file with metadata about the match. Metadata is optional.
        pitch_length: The length of the pitch (in meters). Ignored if metadata that includes pitch length is provided.
        pitch_width: The width of the pitch (in meters). Ignored if metadata that includes pitch width is provided.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        show_progress: Show a progress bar while parsing the data.

    Returns:
        The parsed tracking data.

    Note:
        Pose tracking data is not yet supported.
    """
    ball_feeds = expand_inputs(ball_feeds, regex_filter="samples.ball")
    player_centroid_feeds = expand_inputs(
        player_centroid_feeds, regex_filter="samples.centroids"
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
