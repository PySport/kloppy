from kloppy.domain import Optional, TrackingDataset
from kloppy.infra.serializers.tracking.pff import (
    PFF_TrackingDeserializer,
    PFF_TrackingInputs,
)
from kloppy.io import FileLike, open_as_file


def load_tracking(
    meta_data: FileLike,
    roster_meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
) -> TrackingDataset:
    """
    Load and deserialize tracking data from the provided metadata, roster metadata, and raw data files.

    Args:
        meta_data (FileLike): A file-like object containing metadata about the tracking data.
        roster_meta_data (FileLike): A file-like object containing roster metadata, such as player details.
        raw_data (FileLike): A file-like object containing the raw tracking data.
        sample_rate (Optional[float], optional): The sampling rate to downsample the data. If None, no downsampling is applied. Defaults to None.
        limit (Optional[int], optional): The maximum number of records to process. If None, all records are processed. Defaults to None.
        coordinates (Optional[str], optional): The coordinate system to use for the tracking data (e.g., "pff"). Defaults to None.
        only_alive (Optional[bool], optional): Whether to include only sequences when the ball is in play. Defaults to True.

    Returns:
        TrackingDataset: A deserialized TrackingDataset object containing the processed tracking data.
    """
    deserializer = PFF_TrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        roster_meta_data
    ) as roster_meta_data_fp, open_as_file(raw_data) as raw_data_fp:
        return deserializer.deserialize(
            inputs=PFF_TrackingInputs(
                meta_data=meta_data_fp,
                roster_meta_data=roster_meta_data_fp,
                raw_data=raw_data_fp,
            )
        )
