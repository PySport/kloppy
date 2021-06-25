import os
import re

from pandas import DataFrame
from lxml import objectify

from kloppy import EPTSSerializer
from kloppy.domain import (
    Period,
    AttackingDirection,
    Orientation,
    Point,
    Point3D,
    BallState,
    Team,
    Provider,
)
from kloppy.infra.serializers.tracking.epts.metadata import load_metadata
from kloppy.infra.serializers.tracking.epts.metadata import _load_provider
from kloppy.infra.serializers.tracking.epts.reader import (
    build_regex,
    read_raw_data,
)
from kloppy.utils import performance_logging


class TestEPTSTracking:
    def test_regex(self):
        base_dir = os.path.dirname(__file__)
        with open(f"{base_dir}/files/epts_meta.xml", "rb") as metadata_fp:
            metadata = load_metadata(metadata_fp)

        regex_str = build_regex(
            metadata.data_format_specifications[0],
            metadata.player_channels,
            metadata.sensors,
        )

        regex = re.compile(regex_str)

        # NOTE: use broken example of FIFA
        result = regex.search(
            "1779143:,-2.013,-500,100,9.63,9.80,4,5,177,182;-461,-615,-120,99,900,9.10,4,5,170,179;-2638,3478,120,110,1.15,5.20,3,4,170,175;:-2656,367,100:"
        )

        assert result is not None

    def test_provider_name_recognition(self):
        base_dir = os.path.dirname(__file__)
        with open(
            f"{base_dir}/files/epts_metrica_metadata.xml", "rb"
        ) as metadata_fp:
            root = objectify.fromstring(metadata_fp.read())
            metadata = root.find("Metadata")
            provider_from_file = _load_provider(metadata)

        assert provider_from_file == Provider.METRICA

    def test_read(self):
        base_dir = os.path.dirname(__file__)
        with open(f"{base_dir}/files/epts_meta.xml", "rb") as metadata_fp:
            metadata = load_metadata(metadata_fp)

        with open(f"{base_dir}/files/epts_raw.txt", "rb") as raw_data:
            iterator = read_raw_data(raw_data, metadata)

            with performance_logging("load"):
                assert list(iterator)

    def test_read_to_pandas(self):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_meta.xml", "rb"
        ) as metadata_fp, open(
            f"{base_dir}/files/epts_raw.txt", "rb"
        ) as raw_data:

            metadata = load_metadata(metadata_fp)
            records = read_raw_data(
                raw_data, metadata, sensor_ids=["heartbeat", "position"]
            )
            data_frame = DataFrame.from_records(records)

        assert "player_1_max_heartbeat" in data_frame.columns
        assert "player_1_x" in data_frame.columns

    def test_skip_sensors(self):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_meta.xml", "rb"
        ) as metadata_fp, open(
            f"{base_dir}/files/epts_raw.txt", "rb"
        ) as raw_data:
            metadata = load_metadata(metadata_fp)
            records = read_raw_data(
                raw_data, metadata, sensor_ids=["heartbeat"]
            )
            data_frame = DataFrame.from_records(records)

        assert "player_1_max_heartbeat" in data_frame.columns
        assert "player_1_x" not in data_frame.columns

    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = EPTSSerializer()

        with open(f"{base_dir}/files/epts_meta.xml", "rb") as metadata, open(
            f"{base_dir}/files/epts_raw.txt", "rb"
        ) as raw_data:

            dataset = serializer.deserialize(
                inputs={"metadata": metadata, "raw_data": raw_data}
            )

        first_player = next(iter(dataset.records[0].players_coordinates))

        assert len(dataset.records) == 2
        assert len(dataset.metadata.periods) == 1
        assert dataset.metadata.orientation is None

        assert dataset.records[0].players_coordinates[first_player] == Point(
            x=-769, y=-2013
        )

        assert dataset.records[0].ball_coordinates == Point3D(
            x=-2656, y=367, z=100
        )

    def test_deserialize_metrica_epts(self):
        base_dir = os.path.dirname(__file__)

        serializer = EPTSSerializer()

        with open(
            f"{base_dir}/files/epts_metrica_metadata.xml", "rb"
        ) as metadata, open(
            f"{base_dir}/files/epts_metrica_tracking.txt", "rb"
        ) as raw_data:

            dataset = serializer.deserialize(
                inputs={"metadata": metadata, "raw_data": raw_data}
            )

        first_player = next(iter(dataset.records[0].players_coordinates))

        assert len(dataset.records) == 11
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation is None

        assert dataset.records[0].players_coordinates[first_player] == Point(
            x=0.85708, y=0.50652
        )

        assert dataset.records[0].ball_coordinates == Point3D(
            x=0.54711, y=0.53978, z=None
        )
