import os

import pytest
from kloppy.domain import Point

from kloppy import wyscout


class TestWyscout:
    """"""

    @pytest.fixture
    def event_data(self):
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/wyscout_events.json"

    def test_correct_deserialization(self, event_data: str):
        dataset = wyscout.load(event_data=event_data, coordinates="wyscout")
        assert dataset.records[10].coordinates == Point(23.0, 74.0)

    def test_correct_normalized_deserialization(self, event_data: str):
        dataset = wyscout.load(event_data=event_data)
        assert dataset.records[10].coordinates == Point(0.23, 0.74)
