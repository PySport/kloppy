from typing import List, Optional

from requests.exceptions import HTTPError

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
from kloppy.io import FileLike, open_as_file
from kloppy.utils import deprecated


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


def get_IDSSE_url(match_id: str, data_type: str) -> str:
    """Returns the URL for the meta, event or tracking data for a match in the IDDSE dataset."""
    # match_id -> file_id
    DATA_MAP = {
        "J03WPY": {"meta": 48392497, "event": 48392542, "tracking": 48392572},
        "J03WN1": {"meta": 48392491, "event": 48392527, "tracking": 48392512},
        "J03WMX": {"meta": 48392485, "event": 48392524, "tracking": 48392539},
        "J03WOH": {"meta": 48392515, "event": 48392500, "tracking": 48392578},
        "J03WQQ": {"meta": 48392488, "event": 48392521, "tracking": 48392545},
        "J03WOY": {"meta": 48392503, "event": 48392518, "tracking": 48392551},
        "J03WR9": {"meta": 48392494, "event": 48392530, "tracking": 48392563},
    }
    # URL constant
    DATA_URL = "https://figshare.com/ndownloader/files/{file_id}?private_link=1f806cb3e755c6b54e05"

    if data_type not in ["meta", "event", "tracking"]:
        raise ValueError(
            f"Data type should be one of ['meta', 'event', 'tracking'], but got {data_type}"
        )
    if match_id not in DATA_MAP:
        raise ValueError(
            f"This match_id is not available, please select from {list(DATA_MAP.keys())}"
        )
    return DATA_URL.format(file_id=str(DATA_MAP[match_id][data_type]))


def load_open_event_data(
    match_id: str = "J03WPY",
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load event data for a game from the IDSSE dataset.

    The IDSSE dataset will be released with the publication of the *An integrated
    dataset of synchronized spatiotemporal and event data in elite soccer*
    paper [1]_ and is released under the Creative Commons Attribution 4.0
    license.

    Args:
        match_id (str, optional):
            Match-ID of one of the matches. Defaults to `'J03WPY'`. See below
            for available matches.
        event_types:
        coordinates:
        event_factory:

    Notes:
        The dataset contains seven full matches of raw event and position data
        for both teams and the ball from the German Men's Bundesliga season
        2022/23 first and second division. A detailed description of the
        dataset as well as the collection process can be found in the
        accompanying paper.

        The following matches are available::

        matches = {
            'J03WMX': 1. FC Köln vs. FC Bayern München,
            'J03WN1': VfL Bochum 1848 vs. Bayer 04 Leverkusen,
            'J03WPY': Fortuna Düsseldorf vs. 1. FC Nürnberg,
            'J03WOH': Fortuna Düsseldorf vs. SSV Jahn Regensburg,
            'J03WQQ': Fortuna Düsseldorf vs. FC St. Pauli,
            'J03WOY': Fortuna Düsseldorf vs. F.C. Hansa Rostock,
            'J03WR9': Fortuna Düsseldorf vs. 1. FC Kaiserslautern
        }

    References:
        .. [1] Bassek, M., Weber, H., Rein, R., & Memmert, D. (2024). "An integrated
               dataset of synchronized spatiotemporal and event data in elite soccer."
               In Submission.
    """
    try:
        return load_event(
            event_data=get_IDSSE_url(match_id, "event"),
            meta_data=get_IDSSE_url(match_id, "meta"),
            event_types=event_types,
            coordinates=coordinates,
            event_factory=event_factory,
        )
    except HTTPError as e:
        raise HTTPError(
            "Unable to retrieve data. The dataset archive location may have changed. "
            "See https://github.com/PySport/kloppy/issues/369 for details."
        ) from e


def load_open_tracking_data(
    match_id: str = "J03WPY",
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
) -> TrackingDataset:
    """
    Load tracking data for a game from the IDSSE dataset.

    The IDSSE dataset will be released with the publication of the *An integrated
    dataset of synchronized spatiotemporal and event data in elite soccer*
    paper [1]_ and is released under the Creative Commons Attribution 4.0
    license.

    Args:
        match_id (str, optional):
            Match-ID of one of the matches. Defaults to `'J03WPY'`. See below
            for available matches.
        sampe_rate:
        limit:
        coordinates:
        only_alive:

    Notes:
        The dataset contains seven full matches of raw event and position data
        for both teams and the ball from the German Men's Bundesliga season
        2022/23 first and second division. A detailed description of the
        dataset as well as the collection process can be found in the
        accompanying paper.

        The following matches are available::

        matches = {
            'J03WMX': 1. FC Köln vs. FC Bayern München,
            'J03WN1': VfL Bochum 1848 vs. Bayer 04 Leverkusen,
            'J03WPY': Fortuna Düsseldorf vs. 1. FC Nürnberg,
            'J03WOH': Fortuna Düsseldorf vs. SSV Jahn Regensburg,
            'J03WQQ': Fortuna Düsseldorf vs. FC St. Pauli,
            'J03WOY': Fortuna Düsseldorf vs. F.C. Hansa Rostock,
            'J03WR9': Fortuna Düsseldorf vs. 1. FC Kaiserslautern
        }

    References:
        .. [1] Bassek, M., Weber, H., Rein, R., & Memmert, D. (2024). "An integrated
               dataset of synchronized spatiotemporal and event data in elite soccer."
               In Submission.
    """
    try:
        return load_tracking(
            raw_data=get_IDSSE_url(match_id, "tracking"),
            meta_data=get_IDSSE_url(match_id, "meta"),
            sample_rate=sample_rate,
            limit=limit,
            coordinates=coordinates,
            only_alive=only_alive,
        )
    except HTTPError as e:
        raise HTTPError(
            "Unable to retrieve data. The dataset archive location may have changed. "
            "See https://github.com/PySport/kloppy/issues/369 for details."
        ) from e
