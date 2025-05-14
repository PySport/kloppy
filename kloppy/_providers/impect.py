from kloppy.config import get_config
from kloppy.domain.models.impect.event import ImpectEventFactory
from kloppy.infra.serializers.event.impect import (
    ImpectDeserializer,
    ImpectInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike


def load(
    event_data: FileLike,
    lineup_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Impect event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of json containing the events
        lineup_data: filename of json containing the lineup information
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = ImpectDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory
        or get_config("event_factory")
        or ImpectEventFactory(),
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        lineup_data
    ) as lineup_data_fp:
        return deserializer.deserialize(
            inputs=ImpectInputs(
                event_data=event_data_fp,
                meta_data=lineup_data_fp,
            )
        )
