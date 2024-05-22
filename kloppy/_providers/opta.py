from kloppy.config import get_config
from kloppy.infra.serializers.event.opta import (
    OptaDeserializer,
    OptaInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike


def load(
    f7_data: FileLike,
    f24_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Opta event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        f7_data: filename of json containing the events
        f24_data: filename of json containing the lineup information
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = OptaDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with open_as_file(f7_data) as f7_data_fp, open_as_file(
        f24_data
    ) as f24_data_fp:
        return deserializer.deserialize(
            inputs=OptaInputs(f7_data=f7_data_fp, f24_data=f24_data_fp),
        )
