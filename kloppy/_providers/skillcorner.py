import json
from typing import Optional, Union

from kloppy.domain import TrackingDataset
from kloppy.exceptions import DeserializationError
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
    data_version: Optional[str] = None,
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
        data_version: Specify the input data version.

    Returns:
        The parsed tracking data.
    """
    if data_version not in ["V2", "V3", None]:
        raise ValueError(
            f"data_version must be either 'V2', 'V3'. Provided: {data_version}"
        )
    if not data_version:
        data_version = identify_data_version(raw_data)
    deserializer = SkillCornerDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        include_empty_frames=include_empty_frames,
        data_version=data_version,
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


def identify_data_version(raw_data: FileLike) -> str:
    """
    Identify the data version of the SkillCorner data based on the raw data file.
    Supports both JSONL and JSON formats.
    """
    with open_as_file(raw_data) as raw_data_fp:
        # Extract the first few bytes
        start_byte = raw_data_fp.read(1)
        raw_data_fp.seek(0)

        # Check if it starts with '{' or '['
        if start_byte == b"[":
            # It's a JSON array
            first_line = json.load(raw_data_fp)[0]
        elif start_byte == b"{":
            # It's a JSONL file
            first_line = json.loads(raw_data_fp.readline().strip())
        else:
            raise DeserializationError("Could not determine raw data format")

        # JSONL case: first line is a JSON object
        if "data" in first_line:
            return "V2"
        elif "player_data" in first_line:
            return "V3"

        raise ValueError("Unexpected SkillCorner raw data format")
