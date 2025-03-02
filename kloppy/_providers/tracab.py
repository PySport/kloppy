import warnings
from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.tracab.deserializer import (
    TRACABDeserializer,
    TRACABInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: bool = True,
    file_format: Optional[str] = None,
) -> TrackingDataset:

    # file format is deprecated
    if file_format is not None:
        warnings.warn(
            "file_format is deprecated. This is now automatically infered.",
            DeprecationWarning,
            stacklevel=2,
        )

    deserializer = TRACABDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=TRACABInputs(meta_data=meta_data_fp, raw_data=raw_data_fp)
        )
