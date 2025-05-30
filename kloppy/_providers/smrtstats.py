from kloppy.config import get_config
from kloppy.infra.serializers.event.smrtstats import (
    SmrtStatsDeserializer,
    SmrtStatsInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike


def load(
    raw_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load SmrtStats event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        raw_data:
        event_types:
        coordinates:
        event_factory:
    """

    deserializer = SmrtStatsDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )

    with open_as_file(raw_data) as raw_data_fp:
        return deserializer.deserialize(
            inputs=SmrtStatsInputs(raw_data=raw_data_fp),
        )
