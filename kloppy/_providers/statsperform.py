from typing import List, Optional

from kloppy.domain import (
    EventDataset,
    EventFactory,
    TrackingDataset,
    EventType,
    Provider,
)
from kloppy.infra.serializers.tracking.statsperform import (
    StatsPerformDeserializer as StatsPerformTrackingDeserializer,
    StatsPerformInputs as StatsPerformTrackingInputs,
)
from kloppy.infra.serializers.event.statsperform import (
    StatsPerformDeserializer as StatsPerformEventDeserializer,
    StatsPerformInputs as StatsPerformEventInputs,
)
from kloppy.config import get_config
from kloppy.io import FileLike, open_as_file
from kloppy.utils import deprecated


@deprecated("statsperform.load_tracking should be used")
def load(
    meta_data: FileLike,  # Stats Perform MA1 file - xml or json - single game, live data & lineups
    raw_data: FileLike,  # Stats Perform MA25 file - txt - tracking data
    provider_name: str = "sportvu",
    pitch_length: Optional[float] = None,
    pitch_width: Optional[float] = None,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    if pitch_length is None or pitch_width is None:
        if coordinates is None or coordinates != provider_name:
            raise ValueError(
                "Please provide the pitch dimensions "
                "('pitch_length', 'pitch_width') "
                f"or set 'coordinates' to '{provider_name}'"
            )
    deserializer = StatsPerformTrackingDeserializer(
        provider=Provider[provider_name.upper()],
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with (
        open_as_file(meta_data) as meta_data_fp,
        open_as_file(raw_data) as raw_data_fp,
    ):
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
    event_types: Optional[List[str | EventType]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Stats Perform event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Args:
        ma1_data: MA1 json or xml feed containing the lineup information
        ma3_data: MA3 json or xml feed containing the events
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = StatsPerformEventDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with (
        open_as_file(ma1_data) as ma1_data_fp,
        open_as_file(ma3_data) as ma3_data_fp,
    ):
        return deserializer.deserialize(
            inputs=StatsPerformEventInputs(
                meta_data=ma1_data_fp,
                meta_feed="MA1",
                event_data=ma3_data_fp,
                event_feed="MA3",
            ),
        )


def load_tracking(
    ma1_data: FileLike,
    ma25_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    """
    Load Stats Perform tracking data into a [`TrackingDataset`][kloppy.domain.models.tracking.TrackingDataset]

    Args:
        ma1_data: json or xml feed containing the lineup information
        ma25_data: txt file containing the tracking data
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = StatsPerformTrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with (
        open_as_file(ma1_data) as ma1_data_fp,
        open_as_file(ma25_data) as ma25_data_fp,
    ):
        return deserializer.deserialize(
            inputs=StatsPerformTrackingInputs(
                meta_data=ma1_data_fp, raw_data=ma25_data_fp
            )
        )
