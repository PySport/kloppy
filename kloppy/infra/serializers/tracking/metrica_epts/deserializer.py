import logging
from typing import NamedTuple, IO
from dataclasses import replace

from kloppy.domain import (
    TrackingDataset,
    Provider,
    DatasetTransformer,
)
from kloppy.utils import performance_logging

from .metadata import load_metadata, EPTSMetadata
from ..deserializer import TrackingDataDeserializer
from ..epts_common import create_frame_from_row, read_raw_data

logger = logging.getLogger(__name__)


class MetricaEPTSTrackingDataInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class MetricaEPTSTrackingDataDeserializer(
    TrackingDataDeserializer[MetricaEPTSTrackingDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.METRICA

    @staticmethod
    def _frame_from_row(
        row: dict, metadata: EPTSMetadata, transformer: DatasetTransformer
    ):
        return create_frame_from_row(row, metadata, transformer)

    def deserialize(
        self, inputs: MetricaEPTSTrackingDataInputs
    ) -> TrackingDataset:
        with performance_logging("Loading metadata", logger=logger):
            metadata = load_metadata(inputs.meta_data)

            if metadata.provider and metadata.pitch_dimensions:
                transformer = self.get_transformer(
                    pitch_length=metadata.pitch_dimensions.pitch_length,
                    pitch_width=metadata.pitch_dimensions.pitch_width,
                )
            else:
                transformer = None

        with performance_logging("Loading data", logger=logger):
            # assume they are sorted
            frames = [
                self._frame_from_row(row, metadata, transformer)
                for row in read_raw_data(
                    raw_data=inputs.raw_data,
                    metadata=metadata,
                    sensor_ids=[
                        sensor.sensor_id for sensor in metadata.sensors
                    ],
                    sample_rate=self.sample_rate,
                    limit=self.limit,
                )
            ]

        if transformer:
            metadata = replace(
                metadata,
                pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
                coordinate_system=transformer.get_to_coordinate_system(),
            )

        return TrackingDataset(records=frames, metadata=metadata)
