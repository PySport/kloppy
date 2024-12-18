from typing import Optional, Type, Union

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.tracab.tracab_dat import TRACABDatDeserializer
from kloppy.infra.serializers.tracking.tracab.tracab_json import (
    TRACABInputs,
    TRACABJSONDeserializer,
)
from kloppy.io import FileLike, get_file_extension, open_as_file


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
    file_format: Optional[str] = None,
) -> TrackingDataset:
    """
    Load TRACAB tracking data.

    Args:
        meta_data: A json or dat feed containing the meta data.
        raw_data: A json or dat feed containing the raw tracking data.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        only_alive: Only include frames in which the game is not paused.
        file_format: The format of the tracking data. Supported formats are "dat" and "json".
            If not provided, the format will be inferred based on the file extensions.

    Returns:
        The parsed tracking data.
    """
    if file_format == "dat":
        deserializer_class = TRACABDatDeserializer
    elif file_format == "json":
        deserializer_class = TRACABJSONDeserializer
    else:
        deserializer_class = identify_deserializer(meta_data, raw_data)

    deserializer = deserializer_class(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(raw_data) as raw_data_fp:
        return deserializer.deserialize(
            inputs=TRACABInputs(meta_data=meta_data_fp, raw_data=raw_data_fp)
        )


def identify_deserializer(
    meta_data: FileLike,
    raw_data: FileLike,
) -> Union[Type[TRACABDatDeserializer], Type[TRACABJSONDeserializer]]:
    meta_data_extension = get_file_extension(meta_data)
    raw_data_extension = get_file_extension(raw_data)

    if meta_data_extension == ".xml" and raw_data_extension == ".dat":
        deserializer = TRACABDatDeserializer
    elif meta_data_extension == ".json" and raw_data_extension == ".json":
        deserializer = TRACABJSONDeserializer
    else:
        raise ValueError("Tracab file format could not be recognized, please specify")

    return deserializer
