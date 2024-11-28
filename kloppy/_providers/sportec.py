from typing import Optional, List, Union

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, TrackingDataset
from kloppy.infra.serializers.event.sportec import (
    SportecEventDataDeserializer,
    SportecEventDataInputs,
)
from kloppy.infra.serializers.tracking.sportec import (
    SportecTrackingDataDeserializer,
    SportecTrackingDataInputs,
)
from kloppy.io import open_as_file, FileLike
from kloppy.utils import deprecated

from requests.exceptions import HTTPError


def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Sportec event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of the XML file containing the events
        meta_data: filename of the XML file containing the match information
        event_types:
        coordinates:
        event_factory:

    """
    serializer = SportecEventDataDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return serializer.deserialize(
            SportecEventDataInputs(
                event_data=event_data_fp, meta_data=meta_data_fp
            )
        )


def load_tracking(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
) -> TrackingDataset:
    deserializer = SportecTrackingDataDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=SportecTrackingDataInputs(
                meta_data=meta_data_fp, raw_data=raw_data_fp
            )
        )


@deprecated("sportec.load_event should be used")
def load(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    return load_event(
        event_data, meta_data, event_types, coordinates, event_factory
    )


META_DATA_MAP = {
    "J03WPY": "48392497",
    "J03WN1": "48392491",
    "J03WMX": "48392485",
    "J03WOH": "48392515",
    "J03WQQ": "48392488",
    "J03WOY": "48392503",
    "J03WR9": "48392494",
}
EVENT_DATA_MAP = {
    "J03WPY": "48392542",
    "J03WN1": "48392527",
    "J03WMX": "48392524",
    "J03WOH": "48392500",
    "J03WQQ": "48392521",
    "J03WOY": "48392518",
    "J03WR9": "48392530",
}
TRACKING_DATA_MAP = {
    "J03WPY": "48392572",
    "J03WN1": "48392512",
    "J03WMX": "48392539",
    "J03WOH": "48392578",
    "J03WQQ": "48392545",
    "J03WOY": "48392551",
    "J03WR9": "48392563",
}

DATA_URL = "https://figshare.com/ndownloader/files/{file_id}?private_link=1f806cb3e755c6b54e05"


def load_open_event_data(
    match_id: str = "J03WPY",
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Data associated with research paper:
    Bassek, M., Weber, H., Rein, R., & Memmert, D. (2024).
    "An integrated dataset of synchronized spatiotemporal and event data in elite soccer." In Submission.
    """

    if not META_DATA_MAP.get(match_id):
        raise ValueError(
            f"This match_id is not available, please select from {list(META_DATA_MAP.keys())}"
        )

    try:
        return load_event(
            event_data=DATA_URL.format(file_id=EVENT_DATA_MAP[match_id]),
            meta_data=DATA_URL.format(file_id=META_DATA_MAP[match_id]),
            event_types=event_types,
            coordinates=coordinates,
            event_factory=event_factory,
        )
    except HTTPError as e:
        raise HTTPError(
            "Unable to retrieve data. The dataset archive location may have changed. "
            "Please verify the `kloppy.sportec.DATA_URL` and file mappings. "
            "This issue might be resolved by updating to the latest version of kloppy. "
            "Original error: {}".format(e)
        )


def load_open_tracking_data(
    match_id: str = "J03WPY",
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
) -> EventDataset:
    """
    Data associated with research paper:
    Bassek, M., Weber, H., Rein, R., & Memmert, D. (2024).
    "An integrated dataset of synchronized spatiotemporal and event data in elite soccer." In Submission.
    """

    if not META_DATA_MAP.get(match_id):
        raise ValueError(
            f"This match_id is not available, please select from {list(META_DATA_MAP.keys())}"
        )

    try:
        return load_tracking(
            raw_data=DATA_URL.format(file_id=TRACKING_DATA_MAP[match_id]),
            meta_data=DATA_URL.format(file_id=META_DATA_MAP[match_id]),
            sample_rate=sample_rate,
            limit=limit,
            coordinates=coordinates,
            only_alive=only_alive,
        )
    except HTTPError as e:
        raise HTTPError(
            "Unable to retrieve data. The dataset archive location may have changed. "
            "Please verify the `kloppy.sportec.DATA_URL` and file mappings. "
            "This issue might be resolved by updating to the latest version of kloppy. "
            "Original error: {}".format(e)
        )
