import os
import re

from pandas import DataFrame

from kloppy import EPTSSerializer
from kloppy.domain import (
    Period,
    AttackingDirection,
    Orientation,
    Point,
    BallState,
    Team,
)
from kloppy.infra.serializers.tracking.epts.meta_data import load_meta_data
from kloppy.infra.serializers.tracking.epts.reader import (
    build_regex,
    read_raw_data,
)
from kloppy.infra.utils import performance_logging


class TestEPTSTracking:
    def test_regex(self):
        base_dir = os.path.dirname(__file__)
        with open(f"{base_dir}/files/epts_meta.xml", "rb") as meta_data_fp:
            meta_data = load_meta_data(meta_data_fp)

        regex_str = build_regex(
            meta_data.data_format_specifications[0],
            meta_data.player_channels,
            meta_data.sensors,
        )

        regex = re.compile(regex_str)

        # NOTE: use broken example of FIFA
        result = regex.search(
            "1779143:,-2.013,-500,100,9.63,9.80,4,5,177,182;-461,-615,-120,99,900,9.10,4,5,170,179;-2638,3478,120,110,1.15,5.20,3,4,170,175;:-2656,367,100:"
        )

        assert result is not None

    def test_read(self):
        base_dir = os.path.dirname(__file__)
        with open(f"{base_dir}/files/epts_meta.xml", "rb") as meta_data_fp:
            meta_data = load_meta_data(meta_data_fp)

        with open(f"{base_dir}/files/epts_raw.txt", "rb") as raw_data:
            iterator = read_raw_data(raw_data, meta_data)

            with performance_logging("load"):
                assert list(iterator)

    def test_read_to_pandas(self):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_meta.xml", "rb"
        ) as meta_data_fp, open(
            f"{base_dir}/files/epts_raw.txt", "rb"
        ) as raw_data:

            meta_data = load_meta_data(meta_data_fp)
            records = read_raw_data(
                raw_data, meta_data, sensor_ids=["heartbeat", "position"]
            )
            data_frame = DataFrame.from_records(records)

        assert "player_home_22_max_heartbeat" in data_frame.columns
        assert "player_home_22_x" in data_frame.columns

    def test_skip_sensors(self):
        base_dir = os.path.dirname(__file__)

        with open(
            f"{base_dir}/files/epts_meta.xml", "rb"
        ) as meta_data_fp, open(
            f"{base_dir}/files/epts_raw.txt", "rb"
        ) as raw_data:
            meta_data = load_meta_data(meta_data_fp)
            records = read_raw_data(
                raw_data, meta_data, sensor_ids=["heartbeat"]
            )
            data_frame = DataFrame.from_records(records)

        assert "player_home_22_max_heartbeat" in data_frame.columns
        assert "player_home_22_x" not in data_frame.columns

    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = EPTSSerializer()

        with open(f"{base_dir}/files/epts_meta.xml", "rb") as meta_data, open(
            f"{base_dir}/files/epts_raw.txt", "rb"
        ) as raw_data:

            dataset = serializer.deserialize(
                inputs={"meta_data": meta_data, "raw_data": raw_data}
            )

        assert len(dataset.records) == 2
        assert len(dataset.periods) == 1
        assert dataset.orientation is None

        assert dataset.records[0].home_team_player_positions["22"] == Point(
            x=-769, y=-2013
        )
        assert dataset.records[0].away_team_player_positions == {}
        assert dataset.records[0].ball_position == Point(x=-2656, y=367)
