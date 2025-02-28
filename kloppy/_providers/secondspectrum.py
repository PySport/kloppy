from typing import Optional

from kloppy.domain import TrackingDataset, EventDataset, EventFactory
from kloppy.infra.serializers.tracking.secondspectrum import (
    SecondSpectrumDeserializer,
    SecondSpectrumInputs,
)
from kloppy.infra.serializers.event.secondspectrum import (
    SecondSpectrumEventDataDeserializer,
    SecondSpectrumEventDataInputs,
)
from kloppy.io import FileLike, open_as_file, Source


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    additional_meta_data: Optional[FileLike] = None,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    deserializer = SecondSpectrumDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp, open_as_file(
        Source.create(additional_meta_data, optional=True)
    ) as additional_meta_data_fp:
        return deserializer.deserialize(
            inputs=SecondSpectrumInputs(
                meta_data=meta_data_fp,
                raw_data=raw_data_fp,
                additional_meta_data=additional_meta_data_fp,
            )
        )

def load_event_data(
    meta_data: FileLike,
    event_data: FileLike,
    coordinates: Optional[str] = None,
) -> EventDataset:
    """Load SecondSpectrum event data.

    Parameters
    ----------
    meta_data: str
        Path to metadata json file
    event_data: str
        Path to event data json file
    coordinates: str, optional
        Coordinate system to transform the coordinates to

    Returns
    -------
    EventDataset
    """
    deserializer = SecondSpectrumEventDataDeserializer(coordinate_system=coordinates)
    with open_as_file(meta_data) as meta_data_fp, open_as_file(event_data) as event_data_fp:
        return deserializer.deserialize(
            inputs=SecondSpectrumEventDataInputs(
                meta_data=meta_data_fp,
                event_data=event_data_fp,
                additional_meta_data=None,
            )
        )
    
