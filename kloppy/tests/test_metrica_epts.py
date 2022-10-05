import os
import re

import pytest
from pandas import DataFrame
from lxml import objectify

from kloppy.domain import (
    Point,
    Point3D,
    Provider,
)
from kloppy.infra.serializers.tracking.metrica_epts.metadata import (
    load_metadata,
)
from kloppy.infra.serializers.tracking.metrica_epts.metadata import (
    _load_provider,
)
from kloppy.infra.serializers.tracking.metrica_epts.reader import (
    build_regex,
    read_raw_data,
)
from kloppy.utils import performance_logging


from kloppy import metrica


class TestMetricaEPTSTracking:
    def test_regex(self):
        base_dir = os.path.dirname(__file__)
        with open(
            f"{base_dir}/files/epts_metrica_metadata.xml", "rb"
        ) as metadata_fp:
            metadata = load_metadata(metadata_fp)

        regex_str = build_regex(
            metadata.data_format_specifications[0],
            metadata.player_channels,
            metadata.sensors,
        )

        regex = re.compile(regex_str)

        result = regex.search(
            "450:0.30602,0.97029,5,1.1127902269363403;0.48496,0.73308,1,5.2345757484436035;0.38851,0.97786,2,3.32438325881958;0.48414,0.92730,0,5.878201961517334;0.25661,0.60984,8,4.325275421142578;0.24170,0.49115,7,1.9475973844528198;0.38878,0.47540,4,1.8947187662124634;0.31854,0.89154,3,2.741175413131714;NaN,NaN,-1,NaN;0.25658,0.73095,9,3.418901205062866;NaN,NaN,10,NaN;0.32513,0.89532,19,0.6292267441749573;0.30286,0.98231,17,1.287971019744873;0.39954,0.93079,12,3.8761117458343506;0.23961,0.63742,20,1.6785365343093872;0.38319,0.81908,14,3.611333131790161;0.49984,0.91227,13,5.139825820922852;0.46733,0.49708,16,3.1186790466308594;0.26311,0.48218,18,2.309934139251709;0.53767,0.81373,11,6.402815818786621;0.39631,0.77277,15,3.338606357574463;NaN,NaN,21,NaN:0.52867,0.70690,NaN"
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
        with open(
            f"{base_dir}/files/epts_metrica_metadata.xml", "rb"
        ) as metadata_fp:
            metadata = load_metadata(metadata_fp)

        with open(
            f"{base_dir}/files/epts_metrica_tracking.txt", "rb"
        ) as raw_data:
            iterator = read_raw_data(raw_data, metadata)

            with performance_logging("load"):
                assert list(iterator)

    def test_read_to_pandas(self):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_metrica_metadata.xml", "rb"
        ) as metadata_fp, open(
            f"{base_dir}/files/epts_metrica_tracking.txt", "rb"
        ) as raw_data:

            metadata = load_metadata(metadata_fp)
            records = read_raw_data(
                raw_data, metadata, sensor_ids=["position"]
            )
            data_frame = DataFrame.from_records(records)

        assert "player_Track_1_x" in data_frame.columns

    def test_skip_sensors(self):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_metrica_metadata.xml", "rb"
        ) as metadata_fp, open(
            f"{base_dir}/files/epts_metrica_tracking.txt", "rb"
        ) as raw_data:
            metadata = load_metadata(metadata_fp)
            records = read_raw_data(raw_data, metadata, sensor_ids=["speed"])
            data_frame = DataFrame.from_records(records)

        assert "player_Track_1_s" in data_frame.columns
        assert "player_Track_1_x" not in data_frame.columns

    @pytest.fixture
    def meta_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/epts_metrica_metadata.xml"

    @pytest.fixture
    def raw_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/epts_metrica_tracking.txt"

    def test_correct_deserialization(self, meta_data: str, raw_data: str):
        dataset = metrica.load_tracking_epts(
            meta_data=meta_data, raw_data=raw_data
        )

        first_player = next(iter(dataset.records[0].players_data))

        assert len(dataset.records) == 100
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation is None

        assert dataset.records[0].players_data[
            first_player
        ].coordinates == Point(x=0.30602, y=0.97029)

        assert dataset.records[0].ball_coordinates == Point3D(
            x=0.52867, y=0.7069, z=None
        )

    def test_other_data_deserialization(self, meta_data: str, raw_data: str):
        dataset = metrica.load_tracking_epts(
            meta_data=meta_data, raw_data=raw_data
        )

        first_player = next(iter(dataset.records[0].players_data))

        assert (
            dataset.records[0].players_data[first_player].other_data["mapping"]
            == 5.0
        )

    def test_read_with_sensor_unused_in_players_and_frame_count_name_modified(
        self,
    ):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_metrica_metadata_unused_sensor.xml", "rb"
        ) as metadata_fp, open(
            f"{base_dir}/files/epts_metrica_tracking.txt", "rb"
        ) as raw_data:
            dataset = metrica.load_tracking_epts(
                meta_data=metadata_fp, raw_data=raw_data
            )
        # Acceleration field is in other data
        other_data = list(dataset.frames[0].players_data.items())[0][
            1
        ].other_data
        assert "acceleration" in other_data
        # But is None due to there is not channel for this sensor
        assert other_data["acceleration"] is None
        # But all defined sensors in the metadata are 4
        assert len(dataset.metadata.sensors) == 4
