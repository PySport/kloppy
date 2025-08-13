from typing import Optional, Iterable

from kloppy.domain import TrackingDataset, CoordinateSystem
from kloppy.infra.serializers.tracking.signality import (
    SignalityDeserializer,
    SignalityInputs,
)
from kloppy.io import FileLike, open_as_file, expand_inputs


def load(
    meta_data: FileLike,
    raw_data_feeds: Iterable[FileLike],
    venue_information: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
) -> TrackingDataset:
    """
    Load and deserialize tracking data from multiple input files.

    Args:
        meta_data (FileLike): json feed containing metadata information of the game.
        raw_data_feeds (Iterable[FileLike]): json feeds containing raw tracking data feeds.
        venue_information (FileLike): json feed containing venue information where the game was played.
        sample_rate (Optional[float]): Sampling rate to be applied during deserialization (default: None).
        limit (Optional[int]): Limit on the number of frames to process (default: None).
        coordinates (Optional[str]): Coordinate system to use for deserialization (default: None).

    Returns:
        TrackingDataset: A deserialized tracking dataset object.
    """

    raw_data_feeds = expand_inputs(raw_data_feeds)

    deserializer = SignalityDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
    )

    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        venue_information
    ) as venue_information_fp:
        return deserializer.deserialize(
            inputs=SignalityInputs(
                meta_data=meta_data_fp,
                venue_information=venue_information_fp,
                raw_data_feeds=raw_data_feeds,
            )
        )
