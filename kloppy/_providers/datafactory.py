from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, List, Optional
from kloppy.infra.serializers.event.datafactory import (
    DatafactoryDeserializer,
    DatafactoryInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    event_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load DataFactory event data.

    Args:
        event_data: JSON feed with the raw event data of a game.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.

    Returns:
        The parsed event data.
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
