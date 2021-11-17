from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.skillcorner import (
    SkillCornerDeserializer,
    SkillCornerInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    include_empty_frames: Optional[bool] = False,
) -> TrackingDataset:
    deserializer = SkillCornerDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        include_empty_frames=include_empty_frames,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=SkillCornerInputs(
                meta_data=meta_data_fp, raw_data=raw_data_fp
            )
        )
