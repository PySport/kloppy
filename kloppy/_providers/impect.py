import warnings
from typing import Union

from kloppy.config import get_config
from kloppy.infra.serializers.event.impect import (
    ImpectDeserializer,
    ImpectInputs,
)
from kloppy.domain import EventDataset, Optional, List, EventFactory
from kloppy.io import open_as_file, FileLike, Source


def load(
    event_data: FileLike,
    lineup_data: FileLike,
    squads_data: Optional[FileLike] = None,
    players_data: Optional[FileLike] = None,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load Impect event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Args:
        event_data: JSON feed with the raw event data of a game.
        lineup_data: JSON feed with the corresponding lineup information of the game.
        squads_data: Optional JSON feed with squad information for team names.
        players_data: Optional JSON feed with player information for player names.
        event_types: A list of event types to load. When set, only the specified event types will be loaded.
        coordinates: The coordinate system to use. Defaults to "impect". See [`kloppy.domain.models.common.Provider`][kloppy.domain.models.common.Provider] for available options.
        event_factory: A custom event factory. When set, the factory is used to create event instances.

    Returns:
        The parsed event data.
    """
    deserializer = ImpectDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        lineup_data
    ) as lineup_data_fp, open_as_file(
        Source.create(squads_data, optional=True)
    ) as squads_data_fp, open_as_file(
        Source.create(players_data, optional=True)
    ) as players_data_fp:
        return deserializer.deserialize(
            inputs=ImpectInputs(
                event_data=event_data_fp,
                meta_data=lineup_data_fp,
                squads_data=squads_data_fp,
                players_data=players_data_fp,
            )
        )


def load_open_data(
    match_id: Union[str, int] = "122838",
    competition_id: Union[str, int] = "743",
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
        competition_id: The competition id to load squad and player names from. Defaults to "743".
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

    warnings.warn(
        "\n\nYou are about to use IMPECT public data."
        "\nBy using this data, you are agreeing to the user agreement. "
        "\nThe user agreement can be found here: https://github.com/ImpectAPI/open-data/blob/main/LICENSE.pdf"
        "\n"
    )

    base_url = (
        "https://raw.githubusercontent.com/ImpectAPI/open-data/main/data"
    )

    return load(
        event_data=f"{base_url}/events/events_{match_id}.json",
        lineup_data=f"{base_url}/lineups/lineups_{match_id}.json",
        squads_data=f"{base_url}/squads/squads_{competition_id}.json",
        players_data=f"{base_url}/players/players_{competition_id}.json",
        event_types=event_types,
        coordinates=coordinates,
        event_factory=event_factory,
    )
