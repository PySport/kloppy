from typing import Optional, Union, Type


from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.tracab.tracab_dat import (
    TRACABDatDeserializer,
)
from kloppy.infra.serializers.tracking.tracab.tracab_json import (
    TRACABJSONDeserializer,
    TRACABInputs,
)
from kloppy.io import FileLike, open_as_file, get_file_extension


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
    file_format: Optional[str] = None,
) -> TrackingDataset:
    if file_format == "dat":
        deserializer_class = TRACABDatDeserializer
    elif file_format == "json":
        deserializer_class = TRACABJSONDeserializer
    else:
        deserializer_class = identify_deserializer(raw_data)

    deserializer = deserializer_class(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
        meta_data_extension=get_file_extension(meta_data),
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=TRACABInputs(meta_data=meta_data_fp, raw_data=raw_data_fp)
        )


def identify_deserializer(
    raw_data: FileLike,
) -> Union[Type[TRACABDatDeserializer], Type[TRACABJSONDeserializer]]:

    raw_data_extension = get_file_extension(raw_data)

    if raw_data_extension == ".dat":
        deserializer = TRACABDatDeserializer
    elif raw_data_extension == ".json":
        deserializer = TRACABJSONDeserializer
    else:
        raise ValueError(
            "Tracab file format could not be recognized, please specify"
        )

    return deserializer
