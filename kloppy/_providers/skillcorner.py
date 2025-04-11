import json
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
    data_version: Optional[str] = None,
) -> TrackingDataset:
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
        first_line = raw_data_fp.readline().strip()
        try:
            # Try parsing the first line as JSON
            parsed_data = json.loads(first_line)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON or JSONL format")

        if isinstance(parsed_data, dict):
            # JSONL case: first line is a JSON object
            if "data" in parsed_data:
                return "V2"
            elif "player_data" in parsed_data:
                return "V3"
        elif isinstance(parsed_data, list):
            # JSON case: first element of the list
            if "data" in parsed_data[0]:
                return "V2"
            elif "player_data" in parsed_data[0]:
                return "V3"

        raise ValueError("Unexpected SkillCorner raw data format")
