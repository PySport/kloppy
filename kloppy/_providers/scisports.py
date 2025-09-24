from typing import Optional, List

from kloppy.domain import TrackingDataset
from kloppy.io import FileLike, open_as_file

from kloppy.infra.serializers.tracking.scisports_epts import (
    SciSportsEPTSTrackingDataDeserializer,
    SciSportsEPTSTrackingDataInputs,
)

from kloppy.config import get_config
from kloppy.domain import EventDataset, EventFactory
from kloppy.domain.models.scisports.event import SciSportsEventFactory
from kloppy.infra.serializers.event.scisports import (
    SciSportsDeserializer,
    SciSportsInputs,
)


def load_tracking_epts(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
) -> TrackingDataset:
    """Load SciSports EPTS tracking data.

    Args:
        meta_data: XML metadata file.
        raw_data: positions text file.
        sample_rate: Sampling factor.
        limit: Max number of frames to parse.
        coordinates: Coordinate system to convert to.

    Returns:
        The parsed tracking dataset.
    """
    deserializer = SciSportsEPTSTrackingDataDeserializer(
        sample_rate=sample_rate, limit=limit, coordinate_system=coordinates
    )
    with open_as_file(raw_data) as raw_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return deserializer.deserialize(
            inputs=SciSportsEPTSTrackingDataInputs(
                raw_data=raw_data_fp, meta_data=meta_data_fp
            )
        )


def load_event(
    event_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
    additional_metadata: dict = None,
) -> EventDataset:
    """
    Load SciSports event data.

    Args:
        event_data: JSON feed with the raw event data of a game.
        event_types: A list of event types to load.
        coordinates: The coordinate system to use.
        event_factory: A custom event factory.
        additional_metadata: A dict with additional data that will be added to
            the metadata. See the [`Metadata`][kloppy.domain.Metadata] entity
            for a list of possible keys.

    Returns:
        The parsed event data.
    """
    if additional_metadata is None:
        additional_metadata = {}

    deserializer = SciSportsDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory
        or get_config("event_factory")
        or SciSportsEventFactory(),
    )

    with open_as_file(event_data) as event_data_fp:
        return deserializer.deserialize(
            inputs=SciSportsInputs(event_data=event_data_fp),
            additional_metadata=additional_metadata,
        )
