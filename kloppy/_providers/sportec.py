from typing import List, Optional

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
    Load Sportec Solutions event data.

    Args:
        event_data: XML feed with the raw event data of a game.
        meta_data: XML feed containing the metadata of the game.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.

    Returns:
        The parsed event data.
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
    """
    Load Sportec Solutions tracking data.

    Args:
        meta_data: A json feed containing the metadata of the game.
        raw_data: A json feed containing the raw tracking data.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        only_alive: Only include frames in which the game is not paused.

    Returns:
        The parsed tracking data.
    """
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
        "J03WPY": {"meta": 51643487, "event": 51643505, "tracking": 51643526},
        "J03WN1": {"meta": 51643472, "event": 51643496, "tracking": 51643517},
        "J03WMX": {"meta": 51643475, "event": 51643493, "tracking": 51643514},
        "J03WOH": {"meta": 51643478, "event": 51643499, "tracking": 51643520},
        "J03WQQ": {"meta": 51643484, "event": 51643508, "tracking": 51643529},
        "J03WOY": {"meta": 51643481, "event": 51643502, "tracking": 51643523},
        "J03WR9": {"meta": 51643490, "event": 51643511, "tracking": 51643532},
    }
    # URL constant
    DATA_URL = (
        "https://springernature.figshare.com/ndownloader/files/{file_id}"
    )

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
        .. [1] Bassek, M., Rein, R., Weber, H. et al. "An integrated dataset of
               spatiotemporal and event data in elite soccer." Sci Data 12, 195 (2025).
               https://doi.org/10.1038/s41597-025-04505-y
    """
    return load_event(
        event_data=get_IDSSE_url(match_id, "event"),
        meta_data=get_IDSSE_url(match_id, "meta"),
        event_types=event_types,
        coordinates=coordinates,
        event_factory=event_factory,
    )


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
        sample_rate:
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
    return load_tracking(
        raw_data=get_IDSSE_url(match_id, "tracking"),
        meta_data=get_IDSSE_url(match_id, "meta"),
        sample_rate=sample_rate,
        limit=limit,
        coordinates=coordinates,
        only_alive=only_alive,
    )
