from typing import Optional, Union

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


def load_open_data(
    match_id: Union[str, int] = "4039",
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    include_empty_frames: Optional[bool] = False,
) -> TrackingDataset:
    return load(
        meta_data=f"https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/match_data.json",
        raw_data=f"https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/structured_data.json",
        sample_rate=sample_rate,
        limit=limit,
        coordinates=coordinates,
        include_empty_frames=include_empty_frames,
    )
