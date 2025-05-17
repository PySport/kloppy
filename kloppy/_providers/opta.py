from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, List, Optional
from kloppy.infra.serializers.event.statsperform import (
    StatsPerformDeserializer,
    StatsPerformInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    f7_data: FileLike,
    f24_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Opta event data.

    Args:
        f7_data: F7 xml feed containing the lineup information.
        f24_data: F24 or F73 xml feed containing the events.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.

    Returns:
        The parsed event data.
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
