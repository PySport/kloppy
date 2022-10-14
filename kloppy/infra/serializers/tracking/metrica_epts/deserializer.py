import logging
from typing import NamedTuple, IO
from dataclasses import replace

from kloppy.domain import (
    TrackingDataset,
    Frame,
    Point,
    Point3D,
    Provider,
    PlayerData,
    DatasetTransformer,
)
from kloppy.utils import performance_logging

from .metadata import load_metadata, EPTSMetadata
from .reader import read_raw_data
from ..deserializer import TrackingDataDeserializer

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
    ) -> Frame:
        timestamp = row["timestamp"]
        if metadata.periods and row["period_id"]:
            # might want to search for it instead
            period = metadata.periods[row["period_id"] - 1]
        else:
            period = None

        other_sensors = []
        for sensor in metadata.sensors:
            if sensor.sensor_id not in ["position", "distance", "speed"]:
                other_sensors.append(sensor)

        players_data = {}
        for team in metadata.teams:
            for player in team.players:

                other_data = {}
                for sensor in other_sensors:
                    player_sensor_field_str = f"player_{player.player_id}_{sensor.channels[0].channel_id}"
                    player_sensor_val = row.get(player_sensor_field_str)
                    other_data.update({sensor.sensor_id: player_sensor_val})

                players_data[player] = PlayerData(
                    coordinates=Point(
                        x=row[f"player_{player.player_id}_x"],
                        y=row[f"player_{player.player_id}_y"],
                    )
                    if f"player_{player.player_id}_x" in row
                    else None,
                    speed=row[f"player_{player.player_id}_s"]
                    if f"player_{player.player_id}_s" in row
                    else None,
                    distance=row[f"player_{player.player_id}_d"]
                    if f"player_{player.player_id}_d" in row
                    else None,
                    other_data=other_data,
                )

        frame = Frame(
            frame_id=row["frame_id"],
            timestamp=timestamp,
            ball_owning_team=None,
            ball_state=None,
            period=period,
            players_data=players_data,
            other_data={},
            ball_coordinates=Point3D(
                x=row["ball_x"], y=row["ball_y"], z=row.get("ball_z")
            ),
        )

        if transformer:
            frame = transformer.transform_frame(frame)

        return frame

    def deserialize(
        self, inputs: MetricaEPTSTrackingDataInputs
    ) -> TrackingDataset:
        with performance_logging("Loading metadata", logger=logger):
            metadata = load_metadata(inputs.meta_data)

            if metadata.provider and metadata.pitch_dimensions:
                transformer = self.get_transformer(
                    length=metadata.pitch_dimensions.length,
                    width=metadata.pitch_dimensions.width,
                    provider=metadata.coordinate_system.provider,
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
