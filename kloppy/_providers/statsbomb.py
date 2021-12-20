import warnings
from typing import Union

from kloppy.infra.serializers.event.statsbomb import (
    StatsBombDeserializer,
    StatsbombInputs,
)
from kloppy.domain import EventDataset, Optional, List
from kloppy.io import open_as_file, FileLike


def load(
    event_data: FileLike,
    lineup_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
) -> EventDataset:
    """
    Load Statsbomb event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data: filename of json containing the events
        lineup_data: filename of json containing the lineup information
        event_types:
        coordinates:
    """
    deserializer = StatsBombDeserializer(
        event_types=event_types, coordinate_system=coordinates
    )
    with open_as_file(event_data) as event_data_fp, open_as_file(
        lineup_data
    ) as lineup_data_fp:

        return deserializer.deserialize(
            inputs=StatsbombInputs(
                event_data=event_data_fp, lineup_data=lineup_data_fp
            ),
        )


def load_open_data(
    match_id: Union[str, int] = "15946",
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
) -> EventDataset:
    warnings.warn(
        "\n\nYou are about to use StatsBomb public data."
        "\nBy using this data, you are agreeing to the user agreement. "
        "\nThe user agreement can be found here: https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf"
        "\n"
    )

    return load(
        event_data=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json",
        lineup_data=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/{match_id}.json",
        event_types=event_types,
        coordinates=coordinates,
    )
