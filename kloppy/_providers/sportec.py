from typing import Optional, List

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory
from kloppy.infra.serializers.event.sportec import (
    SportecEventDataDeserializer,
    SportecEvenDataInputs,
)
from kloppy.io import open_as_file
from kloppy.utils import deprecated


def load_event(
    event_data: str,
    meta_data: str,
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
            SportecEvenDataInputs(
                event_data=event_data_fp, meta_data=meta_data_fp
            )
        )


@deprecated("sportec.load_event should be used")
def load(
    event_data: str,
    meta_data: str,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    return load_event(
        event_data, meta_data, event_types, coordinates, event_factory
    )
