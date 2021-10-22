from kloppy.infra.serializers.tracking.metrica_epts.models import Sensor
import logging
from typing import Tuple, Dict, List
from dataclasses import replace

from kloppy.domain import (
    TrackingDataset,
    Frame,
    Point,
    Point3D,
    Transformer,
    build_coordinate_system,
    Provider,
    PlayerData,
)
from kloppy.utils import Readable, performance_logging

from .metadata import load_metadata, EPTSMetadata
from .reader import read_raw_data

from .. import TrackingDataSerializer

logger = logging.getLogger(__name__)


class MetricaEPTSSerializer(TrackingDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "metadata" not in inputs:
            raise ValueError("Please specify a value for 'metadata'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    @staticmethod
    def _frame_from_row(
        row: dict, metadata: EPTSMetadata, transformer: Transformer
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
                    other_data.update(
                        {
                            sensor.sensor_id: row[
                                f"player_{player.player_id}_{sensor.channels[0].channel_id}"
                            ]
                        }
                    )

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
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> TrackingDataset:
        """
        Deserialize Metrica EPTS tracking data into a `TrackingDataset`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'csv' formatted raw data. input `metadata` should point to
            the xml metadata data.
        options : dict
            Options for deserialization of the EPTS file. Possible options are
            `sample_rate` (float between 0 and 1) to specify the amount of
            frames that should be loaded, `limit` to specify the max number of
            frames that will be returned.
        Returns
        -------
        dataset : TrackingDataset
        Raises
        ------
        -

        See Also
        --------

        Examples
        --------
        >>> serializer = MetricaEPTSSerializer()
        >>> with open("metadata.xml", "rb") as meta, \
        >>>      open("raw.dat", "rb") as raw:
        >>>     dataset = serializer.deserialize(
        >>>         inputs={
        >>>             'metadata': meta,
        >>>             'raw_data': raw
        >>>         },
        >>>         options={
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get("sample_rate", 1.0))
        limit = int(options.get("limit", 0))

        with performance_logging("Loading metadata", logger=logger):
            metadata = load_metadata(inputs["metadata"])

            if metadata.provider and metadata.pitch_dimensions:
                to_coordinate_system = build_coordinate_system(
                    options.get("coordinate_system", Provider.KLOPPY),
                    length=metadata.pitch_dimensions.length,
                    width=metadata.pitch_dimensions.width,
                )

                transformer = Transformer(
                    from_coordinate_system=metadata.coordinate_system,
                    to_coordinate_system=to_coordinate_system,
                )
            else:
                transformer = None

        with performance_logging("Loading data", logger=logger):
            # assume they are sorted
            frames = [
                self._frame_from_row(row, metadata, transformer)
                for row in read_raw_data(
                    raw_data=inputs["raw_data"],
                    metadata=metadata,
                    sensor_ids=[
                        sensor.sensor_id for sensor in metadata.sensors
                    ],
                    sample_rate=sample_rate,
                    limit=limit,
                )
            ]

        if transformer:
            metadata = replace(
                metadata,
                pitch_dimensions=to_coordinate_system.pitch_dimensions,
                coordinate_system=to_coordinate_system,
            )

        return TrackingDataset(records=frames, metadata=metadata)

    def serialize(self, dataset: TrackingDataset) -> Tuple[str, str]:
        raise NotImplementedError
