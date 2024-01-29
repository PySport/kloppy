from typing import Optional, Union, Type


from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.tracab.tracab_dat import (
    TRACABDatDeserializer,
    TRACABInputs,
)
from kloppy.infra.serializers.tracking.tracab.tracab_json import (
    TRACABJSONDeserializer,
    TRACABInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = True,
    data_version: Optional[str] = None,
) -> TrackingDataset:
    if data_version == "dat":
        deserializer_class = TRACABDatDeserializer
    elif data_version == "json":
        deserializer_class = TRACABJSONDeserializer
    else:
        deserializer_class = identify_deserializer(meta_data, raw_data)

    deserializer = deserializer_class(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=TRACABInputs(meta_data=meta_data_fp, raw_data=raw_data_fp)
        )


def identify_deserializer(
    meta_data: FileLike,
    raw_data: FileLike,
) -> Union[Type[TRACABDatDeserializer], Type[TRACABJSONDeserializer]]:
    deserializer = None
    if "xml" in meta_data.name and "dat" in raw_data.name:
        deserializer = TRACABDatDeserializer
    if "json" in meta_data.name and "json" in raw_data.name:
        deserializer = TRACABJSONDeserializer

    if deserializer is None:
        raise ValueError(
            "Tracab data version could not be recognized, please specify"
        )

    return deserializer
