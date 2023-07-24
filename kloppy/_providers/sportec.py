from typing import Optional, List

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, TrackingDataset
from kloppy.infra.serializers.event.sportec import (
    SportecEventDataDeserializer,
    SportecEventDataInputs,
)
from kloppy.infra.serializers.tracking.sportec import (
    SportecTrackingDataDeserializer,
    SportecTrackingDataInputs,
)
from kloppy.io import open_as_file, FileLike
from kloppy.utils import deprecated


def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Sportec event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of the XML file containing the events
        meta_data: filename of the XML file containing the match information
        event_types:
        coordinates:
        event_factory:

    """
    serializer = SportecEventDataDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return serializer.deserialize(
            SportecEventDataInputs(
                event_data=event_data_fp, meta_data=meta_data_fp
            )
        )


def load_tracking(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
) -> TrackingDataset:
    deserializer = SportecTrackingDataDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=SportecTrackingDataInputs(
                meta_data=meta_data_fp, raw_data=raw_data_fp
            )
        )


@deprecated("sportec.load_event should be used")
def load(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    return load_event(
        event_data, meta_data, event_types, coordinates, event_factory
    )
