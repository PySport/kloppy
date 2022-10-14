from kloppy.config import get_config
from kloppy.infra.serializers.event.datafactory import (
    DatafactoryDeserializer,
    DatafactoryInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike


def load(
    event_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load DataFactory event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of json containing the events
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = DatafactoryDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with open_as_file(event_data) as event_data_fp:

        return deserializer.deserialize(
            inputs=DatafactoryInputs(event_data=event_data_fp),
        )
