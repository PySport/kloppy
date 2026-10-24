from typing import Optional, Union

from kloppy.domain import EventDataset, EventFactory, Provider, TrackingDataset
from kloppy.domain.models.event import EventType
from kloppy.infra.serializers.event.footovision import (
    FootovisionEventDataDeserializer,
    FootovisionEventDataInputs,
)
from kloppy.infra.serializers.tracking.footovision import (
    FootovisionTrackingDeserializer,
    FootovisionTrackingInputs,
)
from kloppy.io import FileLike, open_as_file


def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[list[Union[EventType, str]]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
    additional_metadata: dict = {},
) -> EventDataset:
    """Load Footovision events and match metadata.

    Source coordinates are normalized from 0 to 1 with a top-left origin.
    Pitch dimensions are read from the match metadata in metres.
    Each period must start at timestamp zero; otherwise, a ValueError is raised.

    Args:
        event_data: Footovision events JSON, supplied as a path, URL or
            file-like object.
        meta_data: Corresponding game JSON containing match metadata,
            teams, lineups and formation history, supplied as a path, URL
            or file-like object.
        event_types: Event types to include, as names such as "pass" and
            "shot", or EventType values. None or an empty list includes all.
        coordinates: Target coordinate system, such as "footovision",
            "secondspectrum" or "statsbomb". None uses Kloppy's configured
            default, falling back to normalized Kloppy coordinates.
        event_factory: Custom EventFactory used to construct event objects.
            None uses the standard EventFactory.
        additional_metadata: Metadata overrides applied after parsing.
            Recognized fields replace the parsed values; unrecognized keys
            are added to metadata.attributes with a warning. These overrides
            do not transform event coordinates; use coordinates for that.

    Returns:
        An EventDataset containing chronologically ordered events and
        match metadata, filtered by event_types when specified.
    """
    deserializer = FootovisionEventDataDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory,
    )
    with (
        open_as_file(event_data) as event_data_fp,
        open_as_file(meta_data) as meta_data_fp,
    ):
        if event_data_fp is None or meta_data_fp is None:
            raise ValueError(
                "FootovisionEventDataDeserializer requires both event_data and meta_data"
            )

        return deserializer.deserialize(
            inputs=FootovisionEventDataInputs(
                event_data=event_data_fp,
                meta_data=meta_data_fp,
            ),
            additional_metadata=additional_metadata,
        )


def load_tracking(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[Union[str, Provider]] = None,
    only_alive: bool = False,
) -> TrackingDataset:
    """Load Footovision tracking data from match metadata and tracking feeds.

    Footovision tracking coordinates are normalized with a top-left origin:
    ``(0, 0)`` is the top-left corner of the pitch. The feed's pitch dimensions
    are expressed in metres and retained in dataset metadata.
    The source feed is sampled at 25 Hz.
    Each period must start at timestamp zero; otherwise, a ValueError is raised.

    Args:
        meta_data: JSON feed containing match and lineup metadata.
        raw_data: JSON feed containing player and ball tracking data.
        sample_rate: Fraction of source frames to retain, in the range ``(0, 1]``.
        limit: Maximum number of frames to return.
        coordinates: Coordinate system for the returned dataset.
        only_alive: Return only frames with a known ball-owning team.

    Raises:
        ValueError: If a required source field is invalid, duplicate ball or
            player records occur at one timestamp, or ``sample_rate`` is out
            of range. Timestamps missing player or ball data are logged and
            skipped.
    """
    deserializer = FootovisionTrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with (
        open_as_file(meta_data) as meta_data_fp,
        open_as_file(raw_data) as raw_data_fp,
    ):
        if meta_data_fp is None or raw_data_fp is None:
            raise ValueError(
                "FootovisionTrackingDeserializer requires both meta_data and raw_data"
            )

        return deserializer.deserialize(
            inputs=FootovisionTrackingInputs(
                meta_data=meta_data_fp, raw_frames=raw_data_fp
            )
        )
