from kloppy.config import get_config
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

    Args:
        event_data: JSON feed with the raw event data of a game.
        lineup_data: JSON feed with the corresponding lineup information of the game.
        event_types: A list of event types to load. When set, only the specified event types will be loaded.
        coordinates: The coordinate system to use. Defaults to "impect". See [`kloppy.domain.models.common.Provider`][kloppy.domain.models.common.Provider] for available options.
        event_factory: A custom event factory. When set, the factory is used to create event instances.

    Returns:
        The parsed event data.
    """
    deserializer = ImpectDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
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
