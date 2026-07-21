from typing import Optional, Union

from kloppy.domain import EventDataset, EventFactory, TrackingDataset
from kloppy.domain.models.event import EventType
from kloppy.infra.serializers.event.footovision import (
    FootovisionEventDataDeserializer,
    FootovisionEventDataInputs,
)
from kloppy.infra.serializers.tracking.footovision import (
    FootovisionTrackingDeserializer,
    FootovisionTrackingInputs,
)
from kloppy.io import FileLike, open_as_file


def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[list[Union[EventType, str]]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
    additional_metadata: dict = {},
) -> EventDataset:
    """
    Load Footovision event data.

    Args:

    Returns:
        The parsed event data.
    """
    deserializer = FootovisionEventDataDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory,
    )
    with (
        open_as_file(event_data) as event_data_fp,
        open_as_file(meta_data) as meta_data_fp,
    ):
        if event_data_fp is None or meta_data_fp is None:
            raise ValueError("FootovisionEventDataDeserializer requires both event_data and meta_data")
        
        return deserializer.deserialize(
            inputs=FootovisionEventDataInputs(
                event_data=event_data_fp,
                meta_data=meta_data_fp,
            ),
            additional_metadata=additional_metadata,
        )


def load_tracking(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: bool = False,
) -> TrackingDataset:
    """Load Footovision tracking data.

    Args:
        meta_data: JSON feed containing match and lineup metadata.
        raw_data: JSON feed containing player and ball tracking data.
        sample_rate: Fraction of source frames to retain.
        limit: Maximum number of frames to return.
        coordinates: Coordinate system for the returned dataset.
        only_alive: Return only frames with a known ball-owning team.
    """
    deserializer = FootovisionTrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with (
        open_as_file(meta_data) as meta_data_fp,
        open_as_file(raw_data) as raw_data_fp,
    ):
        if meta_data_fp is None or raw_data_fp is None:
            raise ValueError("FootovisionTrackingDeserializer requires both meta_data and raw_data")
        
        return deserializer.deserialize(
            inputs=FootovisionTrackingInputs(
                meta_data=meta_data_fp, raw_frames=raw_data_fp
            )
        )
