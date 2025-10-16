from typing import Union

from kloppy.config import get_config
from kloppy.domain.models.impect.event import ImpectEventFactory
from kloppy.infra.serializers.event.impect import (
    ImpectDeserializer,
    ImpectInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike


def load(
    event_data: FileLike,
    lineup_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Impect event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of json containing the events
        lineup_data: filename of json containing the lineup information
        event_types:
        coordinates:
        event_factory:
    """
    deserializer = ImpectDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory
        or get_config("event_factory")
        or ImpectEventFactory(),
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        lineup_data
    ) as lineup_data_fp:
        return deserializer.deserialize(
            inputs=ImpectInputs(
                event_data=event_data_fp,
                meta_data=lineup_data_fp,
            )
        )


def load_open_data(
    match_id: Union[str, int] = "100214",
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Impect open data.

    This function loads event data directly from the ImpectAPI open-data
    GitHub repository.

    Parameters:
        match_id: The id of the match to load data for. Defaults to "100214".
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.

    Returns:
        The parsed event data.

    Examples:
        >>> from kloppy import impect
        >>> dataset = impect.load_open_data(match_id="100214")
        >>> df = dataset.to_df(engine="pandas")
    """
    base_url = (
        "https://raw.githubusercontent.com/ImpectAPI/open-data/main/data"
    )

    return load(
        event_data=f"{base_url}/events/events_{match_id}.json",
        lineup_data=f"{base_url}/lineups/lineups_{match_id}.json",
        event_types=event_types,
        coordinates=coordinates,
        event_factory=event_factory,
    )
