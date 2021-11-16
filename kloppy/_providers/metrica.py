from typing import Optional, List

from kloppy.infra.serializers.event.metrica import (
    MetricaEventsJsonDeserializer,
    MetricaEventsJsonInputs,
)
from kloppy.io import FileLike, open_as_file


def load_tracking_csv():
    pass


def load_tracking_epts():
    pass


def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
):
    deserializer = MetricaEventsJsonDeserializer(
        event_types=event_types, coordinate_system=coordinates
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return deserializer.deserialize(
            inputs=MetricaEventsJsonInputs(
                event_data=event_data_fp, meta_data=meta_data_fp
            ),
        )
