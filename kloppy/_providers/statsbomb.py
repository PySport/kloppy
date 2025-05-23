import warnings
from typing import Union

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory, List, Optional
from kloppy.domain.models.statsbomb.event import StatsBombEventFactory
from kloppy.infra.serializers.event.statsbomb import (
    StatsBombDeserializer,
    StatsBombInputs,
)
from kloppy.io import FileLike, Source, open_as_file


def load(
    event_data: FileLike,
    lineup_data: FileLike,
    three_sixty_data: Optional[FileLike] = None,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
    additional_metadata: dict = {},
) -> EventDataset:
    """
    Load StatsBomb event data.

    Args:
        event_data: JSON feed with the raw event data of a game.
        lineup_data: JSON feed with the corresponding lineup information of the game.
        three_sixty_data: JSON feed with the 360 freeze frame data of the game.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.
        additional_metadata: A dict with additional data that will be added to
            the metadata. See the [`Metadata`][kloppy.domain.Metadata] entity
            for a list of possible keys.

    Returns:
        The parsed event data.
    """
    deserializer = StatsBombDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory
        or get_config("event_factory")
        or StatsBombEventFactory(),
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        lineup_data
    ) as lineup_data_fp, open_as_file(
        Source.create(three_sixty_data, optional=True)
    ) as three_sixty_data_fp:
        return deserializer.deserialize(
            inputs=StatsBombInputs(
                event_data=event_data_fp,
                lineup_data=lineup_data_fp,
                three_sixty_data=three_sixty_data_fp,
            ),
            additional_metadata=additional_metadata,
        )


def load_open_data(
    match_id: Union[str, int] = "15946",
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    """
    Load StatsBomb open data.

    This function loads event data directly from the StatsBomb open data
    GitHub repository.

    Args:
        match_id: The id of the match to load data for.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.

    Returns:
        The parsed event data.
    """
    warnings.warn(
        "\n\nYou are about to use StatsBomb public data."
        "\nBy using this data, you are agreeing to the user agreement. "
        "\nThe user agreement can be found here: https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf"
        "\n"
    )

    return load(
        event_data=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json",
        lineup_data=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/{match_id}.json",
        three_sixty_data=Source(
            f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/three-sixty/{match_id}.json",
            skip_if_missing=True,
        ),
        event_types=event_types,
        coordinates=coordinates,
        event_factory=event_factory,
    )
