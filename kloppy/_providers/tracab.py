from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.tracab import (
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
    only_alive: Optional[bool] = True,
) -> TrackingDataset:
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
