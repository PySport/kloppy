import json
from typing import Union

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
    if data_version not in ["V3", "V2"]:
        data_version = identify_data_version(event_data)

    if data_version == "V3":
        deserializer = WyscoutDeserializerV3(
            event_types=event_types,
            coordinate_system=coordinates,
            event_factory=event_factory or get_config("event_factory"),
        )
    elif data_version == "V2":
        deserializer = WyscoutDeserializerV2(
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
        event_data=f"https://raw.githubusercontent.com/koenvo/wyscout-soccer-match-event-dataset/main/processed/files/{match_id}.json",
        event_types=event_types,
        coordinates=coordinates,
        event_factory=event_factory,
    )


def identify_data_version(event_data: FileLike) -> str:
    with open(event_data) as json_file:
        events_with_meta = json.load(json_file)
    events = events_with_meta["events"]
    first_event = events[0]
    if "eventName" in first_event:
        data_version = "V2"
        return data_version
    elif "primary" in first_event.get("type", {}):
        data_version = "V3"
        return data_version
    else:
        raise ValueError(
            "Wyscout data model could not be recognized, please specify"
        )
