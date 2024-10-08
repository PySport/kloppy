from kloppy.config import get_config
from kloppy.infra.serializers.event.statsperform import (
    StatsPerformDeserializer,
    StatsPerformInputs,
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
        f7_data: F7 xml feed containing the lineup information
        f24_data: F24 xml feed containing the events
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = StatsPerformDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with open_as_file(f7_data) as f7_data_fp, open_as_file(
        f24_data
    ) as f24_data_fp:
        return deserializer.deserialize(
            inputs=StatsPerformInputs(
                meta_data=f7_data_fp,
                meta_feed="F7",
                meta_datatype="XML",
                event_data=f24_data_fp,
                event_feed="F24",
                event_datatype="XML",
            ),
        )
