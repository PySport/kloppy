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
    """
    Load SkillCorner broadcast tracking data.

    Args:
        meta_data: A json feed containing the meta data.
        raw_data: A json feed containing the raw tracking data.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        include_empty_frames: Include frames in which no objects were tracked.

    Returns:
        The parsed tracking data.
    """
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
    """
    Load SkillCorner open data.

    This function loads tracking data directly from the SkillCorner open data
    GitHub repository.

    Args:
        match_id: The id of the match to load data for.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        include_empty_frames: Include frames in which no objects were tracked.

    Returns:
        The parsed tracking data.
    """
    return load(
        meta_data=f"https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/match_data.json",
        raw_data=f"https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/structured_data.json",
        sample_rate=sample_rate,
        limit=limit,
        coordinates=coordinates,
        include_empty_frames=include_empty_frames,
    )
