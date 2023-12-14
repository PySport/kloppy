import json
from typing import Union, Type

from kloppy.config import get_config
from kloppy.infra.serializers.event.wyscout import (
    WyscoutDeserializerV3,
    WyscoutDeserializerV2,
    WyscoutInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike


def load(
    event_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
    data_version: Optional[str] = None,
) -> EventDataset:
    """
    Load Wyscout event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of the XML file containing the events and metadata
        event_types:
        coordinates:
        event_factory:
        data_version:
    """
    if data_version == "V2":
        deserializer_class = WyscoutDeserializerV2
    elif data_version == "V3":
        deserializer_class = WyscoutDeserializerV3
    else:
        deserializer_class = identify_deserializer(event_data)

    deserializer = deserializer_class(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )

    with open_as_file(event_data) as event_data_fp:
        return deserializer.deserialize(
            inputs=WyscoutInputs(event_data=event_data_fp),
        )


def load_open_data(
    match_id: Union[str, int] = "2499841",
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    return load(
        event_data=f"https://raw.githubusercontent.com/koenvo/wyscout-soccer-match-event-dataset/main/processed-v2/files/{match_id}.json",
        event_types=event_types,
        coordinates=coordinates,
        event_factory=event_factory,
    )


def identify_deserializer(
    event_data: FileLike,
) -> Union[Type[WyscoutDeserializerV3], Type[WyscoutDeserializerV2]]:
    with open_as_file(event_data) as event_data_fp:
        events_with_meta = json.load(event_data_fp)

    events = events_with_meta["events"]
    first_event = events[0]

    deserializer = None
    if "eventName" in first_event:
        deserializer = WyscoutDeserializerV2
    elif "primary" in first_event.get("type", {}):
        deserializer = WyscoutDeserializerV3

    if deserializer is None:
        raise ValueError(
            "Wyscout data version could not be recognized, please specify"
        )

    return deserializer
