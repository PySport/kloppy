from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.secondspectrum import (
    SecondSpectrumDeserializer,
    SecondSpectrumInputs,
)
from kloppy.io import FileLike, Source, open_as_file


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    additional_meta_data: Optional[FileLike] = None,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    """
    Load SecondSpectrum tracking data.

    Args:
        meta_data: A json or xml feed containing the meta data.
        raw_data: A json feed containing the raw tracking data.
        additional_meta_data: A dict with additional data that will be added to
            the metadata. See the [`Metadata`][kloppy.domain.Metadata] entity
            for a list of possible keys.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        only_alive: Only include frames in which the game is not paused.

    Returns:
        The parsed tracking data.
    """
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
