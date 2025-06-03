from kloppy.domain import TrackingDataset, EventDataset
from kloppy.domain.services.event_factory import EventFactory
from kloppy.infra.serializers.tracking.pff import (
    PFFTrackingDeserializer,
    PFFTrackingInputs,
)
from kloppy.infra.serializers.event.pff import PFFEventDeserializer, PFFEventInputs
from kloppy.io import FileLike, open_as_file
from kloppy.config import get_config


def load_tracking(
    meta_data: FileLike,
    roster_meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: float | None = None,
    limit: int | None = None,
    coordinates: str | None = None,
    only_alive: bool | None = True,
) -> TrackingDataset:
    """
    Load and deserialize tracking data from the provided metadata, roster metadata, and raw data files.

    Args:
        meta_data (FileLike): A file-like object containing metadata about the tracking data.
        roster_meta_data (FileLike): A file-like object containing roster metadata, such as player details.
        raw_data (FileLike): A file-like object containing the raw tracking data.
        sample_rate (Optional[float], optional): The sampling rate to downsample the data. If None, no downsampling is applied. Defaults to None.
        limit (Optional[int], optional): The maximum number of records to process. If None, all records are processed. Defaults to None.
        coordinates (Optional[str], optional): The coordinate system to use for the tracking data (e.g., "pff"). Defaults to None.
        only_alive (Optional[bool], optional): Whether to include only sequences when the ball is in play. Defaults to True.

    Returns:
        TrackingDataset: A deserialized TrackingDataset object containing the processed tracking data.
    """
    deserializer = PFFTrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        roster_meta_data
    ) as roster_meta_data_fp, open_as_file(raw_data) as raw_data_fp:
        return deserializer.deserialize(
            inputs=PFFTrackingInputs(
                meta_data=meta_data_fp,
                roster_meta_data=roster_meta_data_fp,
                raw_data=raw_data_fp,
            )
        )

def load_event(
    metadata: FileLike,
    players: FileLike,
    raw_event_data: FileLike,
    event_types: list[str] | None = None,
    coordinates: str | None = None,
    event_factory: EventFactory | None = None,
    additional_metadata: dict = {},
) -> EventDataset:
    """
    Load PFF event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        match_metadata (FileLike): A file-like object containing metadata about the match.
        roster_metadata (FileLike): filename of json containing the lineup information
        raw_event_data (FileLike): filename of json containing the events
        event_types (List[str], optional): A list of event types to filter the events. If None, all events are included. Defaults to None.
        coordinates (str, optional): The coordinate system to use for the tracking data. Defaults to None.
        event_factory: (EventFactory, optional): An optional event factory to use for creating events. If None, the default event factory is used. Defaults to None.
        additional_metadata (dict, optional): Additional metadata to include in the deserialization process. Defaults to an empty dictionary.
    """
    deserializer = PFFEventDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory")
    )

    with (
        open_as_file(metadata) as metadata_fp,
        open_as_file(players) as players_fp,
        open_as_file(raw_event_data) as raw_event_data_fp
    ):
        return deserializer.deserialize(
            inputs=PFFEventInputs(
                metadata=metadata_fp,
                players=players_fp,
                raw_event_data=raw_event_data_fp,
            ),
            additional_metadata=additional_metadata,
        )
