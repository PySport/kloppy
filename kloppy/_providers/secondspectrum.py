from typing import Optional
import contextlib

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.secondspectrum import (
    SecondSpectrumDeserializer,
    SecondSpectrumInputs,
)
from kloppy.io import FileLike, open_as_file


@contextlib.contextmanager
def dummy_context_mgr():
    yield None


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    additional_meta_data: Optional[FileLike] = None,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: Optional[bool] = False,
) -> TrackingDataset:
    deserializer = SecondSpectrumDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp, open_as_file(
        additional_meta_data
    ) if additional_meta_data else dummy_context_mgr() as additional_meta_data_fp:
        return deserializer.deserialize(
            inputs=SecondSpectrumInputs(
                meta_data=meta_data_fp,
                raw_data=raw_data_fp,
                additional_meta_data=additional_meta_data_fp,
            )
        )
