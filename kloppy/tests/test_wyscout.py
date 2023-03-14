import os

import pytest
from kloppy.domain import Point

from kloppy import wyscout


class TestWyscout:
    """"""

    @pytest.fixture
    def event_v3_data(self):
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/wyscout_events_v3.json"

    @pytest.fixture
    def event_v2_data(self):
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/wyscout_events_v2.json"

    def test_correct_v3_deserialization(self, event_v3_data: str):
        dataset = wyscout.load(
            event_data=event_v3_data,
            coordinates="wyscout",
            data_version="V3",
        )
        assert dataset.records[2].coordinates == Point(36.0, 78.0)

    def test_correct_normalized_v3_deserialization(self, event_v3_data: str):
        dataset = wyscout.load(event_data=event_v3_data, data_version="V3")
        assert dataset.records[2].coordinates == Point(0.36, 0.78)

    def test_correct_v2_deserialization(self, event_v2_data: str):
        dataset = wyscout.load(
            event_data=event_v2_data,
            coordinates="wyscout",
            data_version="V2",
        )
        assert dataset.records[2].coordinates == Point(29.0, 6.0)

    def test_correct_auto_recognize_deserialization(self, event_v2_data: str):
        dataset = wyscout.load(event_data=event_v2_data, coordinates="wyscout")
        assert dataset.records[2].coordinates == Point(29.0, 6.0)
