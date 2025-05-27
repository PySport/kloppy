from typing import Optional, Union

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.respovision import (
    RespoVisionDeserializer,
    RespoVisionInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    include_empty_frames: Optional[bool] = False,
    pitch_width: Optional[float] = 68.0,
    pitch_length: Optional[float] = 105.0,
) -> TrackingDataset:
    deserializer = RespoVisionDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        include_empty_frames=include_empty_frames,
        pitch_width=pitch_width,
        pitch_length=pitch_length,
    )
    with open_as_file(raw_data) as raw_data_fp:
        return deserializer.deserialize(
            inputs=RespoVisionInputs(raw_data=raw_data_fp)
        )
