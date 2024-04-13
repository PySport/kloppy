"""Functions to load Stats Perform data."""
from typing import List, Optional

from kloppy.config import get_config
from kloppy.domain import (
    EventDataset,
    EventFactory,
    Provider,
    TrackingDataset,
)
from kloppy.infra.serializers.event.statsperform import (
    StatsPerformInputs as StatsPerformEventInputs,
    StatsPerformDeserializer as StatsPerformEventDeserializer,
)
from kloppy.infra.serializers.tracking.statsperform import (
    StatsPerformInputs as StatsPerformTrackingInputs,
    StatsPerformDeserializer as StatsPerformTrackingDeserializer,
)
from kloppy.io import FileLike, open_as_file
from kloppy.utils import deprecated


@deprecated("statsperform.load_tracking should be used")
def load(
    meta_data: FileLike,  # Stats Perform MA1 file - xml or json - single game, live data & lineups
    raw_data: FileLike,  # Stats Perform MA25 file - txt - tracking data
    tracking_system: str = "sportvu",
    pitch_length: Optional[float] = None,
    pitch_width: Optional[float] = None,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    deserializer = StatsPerformTrackingDeserializer(
        provider=Provider[tracking_system.upper()],
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=StatsPerformTrackingInputs(
                meta_data=meta_data_fp,
                raw_data=raw_data_fp,
                pitch_length=pitch_length,
                pitch_width=pitch_width,
            )
        )


def load_event(
    ma1_data: FileLike,
    ma3_data: FileLike,
    pitch_length: Optional[float] = None,
    pitch_width: Optional[float] = None,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """Load Stats Perform event data.

    Args:
        ma1_data: MA1 json or xml feed containing the lineup information
        ma3_data: MA3 json or xml feed containing the events
        pitch_length: length of the pitch (in meters)
        pitch_width: width of the pitch (in meters)
        event_types: list of event types to load
        coordinates: coordinate system to use
        event_factory: a custom event factory

    Returns:
        EventDataset: the loaded event data
    """
    deserializer = StatsPerformEventDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),  # type: ignore
    )
    with open_as_file(ma1_data) as ma1_data_fp, open_as_file(
        ma3_data
    ) as ma3_data_fp:
        return deserializer.deserialize(
            inputs=StatsPerformEventInputs(
                meta_data=ma1_data_fp,
                meta_feed="MA1",
                event_data=ma3_data_fp,
                event_feed="MA3",
                pitch_length=pitch_length,
                pitch_width=pitch_width,
            ),
        )


def load_tracking(
    ma1_data: FileLike,
    ma25_data: FileLike,
    tracking_system: str = "sportvu",
    pitch_length: Optional[float] = None,
    pitch_width: Optional[float] = None,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    """
    Load Stats Perform tracking data.

    Args:
        ma1_data: json or xml feed containing the lineup information
        ma25_data: txt file containing the tracking data
        tracking_system: system that generated the tracking data
        pitch_length: length of the pitch (in meters)
        pitch_width: width of the pitch (in meters)
        sample_rate: sample the data at a specific rate
        limit: limit the number of frames loaded
        coordinates: coordinate system to use
        only_alive: only include frames in which the game is not paused

    Returns:
        TrackingDataset: the loaded tracking data
    """
    deserializer = StatsPerformTrackingDeserializer(
        provider=Provider[tracking_system.upper()],
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(ma1_data) as ma1_data_fp, open_as_file(
        ma25_data
    ) as ma25_data_fp:
        return deserializer.deserialize(
            inputs=StatsPerformTrackingInputs(
                meta_data=ma1_data_fp,
                raw_data=ma25_data_fp,
                pitch_length=pitch_length,
                pitch_width=pitch_width,
            )
        )
