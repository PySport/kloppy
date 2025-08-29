from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.io import FileLike, open_as_file

from kloppy.infra.serializers.tracking.scisports_epts import (
    SciSportsEPTSTrackingDataDeserializer,
    SciSportsEPTSTrackingDataInputs,
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
