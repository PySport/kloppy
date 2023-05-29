from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.statsperform import (
    StatsPerformDeserializer,
    StatsPerformInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    meta_data: FileLike,  # Stats Perform MA1 file - xml - single game, live data & lineups
    raw_data: FileLike,  # Stats Perform MA25 file - txt - tracking data
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    deserializer = StatsPerformDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=StatsPerformInputs(
                meta_data=meta_data_fp, raw_data=raw_data_fp
            )
        )
