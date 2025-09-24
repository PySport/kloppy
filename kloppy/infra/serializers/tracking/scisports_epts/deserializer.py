import logging
import re
import warnings
from typing import NamedTuple, IO
from dataclasses import replace

from kloppy.domain import (
    TrackingDataset,
    Provider,
    DatasetTransformer,
    Orientation,
    AttackingDirection,
)
from kloppy.utils import performance_logging
from kloppy.domain.services import attacking_direction_from_frame

from ..deserializer import TrackingDataDeserializer
from ..metrica_epts.metadata import EPTSMetadata
from ..epts_common import create_frame_from_row, read_raw_data
from .metadata import load_metadata

logger = logging.getLogger(__name__)


class SciSportsEPTSTrackingDataInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]


class SciSportsEPTSTrackingDataDeserializer(
    TrackingDataDeserializer[SciSportsEPTSTrackingDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.SCISPORTS

    @staticmethod
    def _frame_from_row(
        row: dict, metadata: EPTSMetadata, transformer: DatasetTransformer
    ):
        return create_frame_from_row(
            row, metadata, transformer, swap_coordinates=True
        )

    def deserialize(
        self, inputs: SciSportsEPTSTrackingDataInputs
    ) -> TrackingDataset:
        with performance_logging("Loading metadata", logger=logger):
            metadata = load_metadata(inputs.meta_data)

            if metadata.pitch_dimensions:
                transformer = self.get_transformer(
                    pitch_length=metadata.pitch_dimensions.pitch_length,
                    pitch_width=metadata.pitch_dimensions.pitch_width,
                    provider=self.provider,
                )
            else:
                transformer = None

        with performance_logging("Loading data", logger=logger):
            all_frames = [
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

            # Filter out frames that don't belong to any period (pre/post-match frames)
            frames = [
                frame for frame in all_frames if frame.period is not None
            ]

            if len(frames) < len(all_frames):
                logger.info(
                    f"Filtered out {len(all_frames) - len(frames)} frames "
                    f"that don't belong to any period (pre/post-match frames)"
                )

        # Determine orientation from first frame analysis
        try:
            first_frame = next(
                frame
                for frame in frames
                if frame.period and frame.period.id == 1
            )
            orientation = (
                Orientation.HOME_AWAY
                if attacking_direction_from_frame(first_frame)
                == AttackingDirection.LTR
                else Orientation.AWAY_HOME
            )
        except StopIteration:
            warnings.warn(
                "Could not determine orientation of dataset, defaulting to NOT_SET"
            )
            orientation = Orientation.NOT_SET

        if transformer:
            metadata = replace(
                metadata,
                pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
                coordinate_system=transformer.get_to_coordinate_system(),
                orientation=orientation,
            )
        else:
            metadata = replace(metadata, orientation=orientation)

        return TrackingDataset(records=frames, metadata=metadata)
