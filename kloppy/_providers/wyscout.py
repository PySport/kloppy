import json
from typing import Type, Union

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, List, Optional
from kloppy.infra.serializers.event.wyscout import (
    WyscoutDeserializerV2,
    WyscoutDeserializerV3,
    WyscoutInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    event_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
    data_version: Optional[str] = None,
) -> EventDataset:
    """
    Load Wyscout event data.

    Args:
        event_data: JSON feed with the raw event data of a game.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.
        data_version: The version of the Wyscout data. Supported versions are "V2" and "V3".

    Returns:
        The parsed event data.
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
    """
    Load Wyscout open data.

    This dataset is a public release of event stream data, collected by Wyscout
    containing all matches of the 2017/18 season of the top-5 European leagues
    (La Liga, Serie A, Bundesliga, Premier League, Ligue 1), the FIFA World
    Cup 2018, and UEFA Euro Cup 2016. For a detailed description,
    see Pappalardo et al. [1].

    Args:
        match_id: The id of the match to load data for.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.

    Returns:
        The parsed event data.

    References:
        [1] Pappalardo, L., Cintia, P., Rossi, A. et al. A public data set of spatio-temporal match events in soccer competitions. Sci Data 6, 236 (2019). https://doi.org/10.1038/s41597-019-0247-7
    """
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
