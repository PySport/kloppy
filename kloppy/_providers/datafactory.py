from kloppy.infra.serializers.event.datafactory import (
    DatafactoryDeserializer,
    DatafactoryInputs,
)
from kloppy.domain import EventDataset, Optional, List
from kloppy.io import open_as_file, FileLike


def load(
    event_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
) -> EventDataset:
    """
    Load DataFactory event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of json containing the events
        event_types:
        coordinates:
    """
    deserializer = DatafactoryDeserializer(
        event_types=event_types, coordinate_system=coordinates
    )
    with open_as_file(event_data) as event_data_fp:

        return deserializer.deserialize(
            inputs=DatafactoryInputs(event_data=event_data_fp),
        )
