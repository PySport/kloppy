from typing import Optional, Union

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.signality import (
    SignalityDeserializer,
    SignalityInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    meta_data: FileLike,
    p1_raw_data: FileLike,
    p2_raw_data: FileLike,
    venue_information: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
) -> TrackingDataset:
    deserializer = SignalityDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        venue_information
    ) as venue_information_fp, open_as_file(
        p1_raw_data
    ) as p1_raw_data_fp, open_as_file(
        p2_raw_data
    ) as p2_raw_data_fp:
        return deserializer.deserialize(
            inputs=SignalityInputs(
                meta_data=meta_data_fp,
                venue_information=venue_information_fp,
                p1_raw_data=p1_raw_data_fp,
                p2_raw_data=p2_raw_data_fp,
            )
        )
