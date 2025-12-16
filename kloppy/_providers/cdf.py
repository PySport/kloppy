from typing import Optional, Union

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, TrackingDataset
from kloppy.exceptions import KloppyError

from kloppy.infra.serializers.tracking.cdf import (
    CDFTrackingDeserializer,
    CDFTrackingDataInputs,
)
from kloppy.io import FileLike, open_as_file


def load_tracking(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    include_empty_frames: Optional[bool] = False,
    only_alive: Optional[bool] = True,
) -> TrackingDataset:
    """
    Load Common Data Format broadcast tracking data.

    Args:
        meta_data: A JSON feed containing the meta data.
        raw_data: A JSONL feed containing the raw tracking data.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        include_empty_frames: Include frames in which no objects were tracked.
        only_alive: Only include frames in which the game is not paused.

    Returns:
        The parsed tracking data.
    """
    deserializer = CDFTrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        include_empty_frames=include_empty_frames,
        only_alive=only_alive,
    )
    with (
        open_as_file(meta_data) as meta_data_fp,
        open_as_file(raw_data) as raw_data_fp,
    ):
        return deserializer.deserialize(
            inputs=CDFTrackingDataInputs(
                meta_data=meta_data_fp, raw_data=raw_data_fp
            )
        )


# def load_event(
#     event_data: FileLike,
#     meta_data: FileLike,
#     event_types: Optional[list[str]] = None,
#     coordinates: Optional[str] = None,
#     event_factory: Optional[EventFactory] = None,
# ) -> EventDataset:
#     """
#     Load Common Data Format event data.

#     Args:
#         event_data: JSON feed with the raw event data of a game.
#         meta_data: JSON feed with the corresponding lineup information of the game.
#         event_types: A list of event types to load.
#         coordinates: The coordinate system to use.
#         event_factory: A custom event factory.

#     Returns:
#         The parsed event data.
#     """
#     deserializer = StatsBombDeserializer(
#         event_types=event_types,
#         coordinate_system=coordinates,
#         event_factory=event_factory
#         or get_config("event_factory")
#         or StatsBombEventFactory(),
#     )
#     with (
#         open_as_file(event_data) as event_data_fp,
#         open_as_file(meta_data) as meta_data_fp,
#     ):
#         return deserializer.deserialize(
#             inputs=StatsBombInputs(
#                 event_data=event_data_fp,
#                 lineup_data=meta_data_fp,
#             )
#         )
