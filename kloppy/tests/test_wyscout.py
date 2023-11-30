from pathlib import Path

import pytest
from kloppy.domain import (
    Point,
    SetPieceType,
    SetPieceQualifier,
    DuelQualifier,
    DuelType,
    EventType,
    GoalkeeperQualifier,
    GoalkeeperActionType,
)

from kloppy import wyscout


class TestWyscout:
    """"""

    @pytest.fixture
    def event_v3_data(self, base_dir):
        return base_dir / "files/wyscout_events_v3.json"

    @pytest.fixture
    def event_v2_data(self, base_dir):
        return base_dir / "files/wyscout_events_v2.json"

    def test_correct_v3_deserialization(self, event_v3_data: Path):
        dataset = wyscout.load(
            event_data=event_v3_data,
            coordinates="wyscout",
            data_version="V3",
        )
        assert dataset.records[2].coordinates == Point(36.0, 78.0)
        assert (
            dataset.events[10].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )
        assert (
            dataset.events[4].get_qualifier_value(SetPieceQualifier)
            == SetPieceType.CORNER_KICK
        )
        assert dataset.events[5].event_type == EventType.FOUL_COMMITTED
        assert (
            dataset.events[6].get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        assert DuelQualifier(value=DuelType.OFFENSIVE) in dataset.events[
            6
        ].get_qualifier_values(DuelQualifier)
        assert (
            dataset.events[7].get_qualifier_values(DuelQualifier)[1].value
            == DuelType.AERIAL
        )
        assert (
            dataset.events[8].get_qualifier_values(DuelQualifier)[2].value
            == DuelType.SLIDING_TACKLE
        )
        assert dataset.events[9].event_type == EventType.CLEARANCE
        assert dataset.events[12].event_type == EventType.INTERCEPTION

    def test_correct_normalized_v3_deserialization(self, event_v3_data: Path):
        dataset = wyscout.load(event_data=event_v3_data, data_version="V3")
        assert dataset.records[2].coordinates == Point(0.36, 0.78)

    def test_correct_v2_deserialization(self, event_v2_data: Path):
        dataset = wyscout.load(
            event_data=event_v2_data,
            coordinates="wyscout",
            data_version="V2",
        )
        assert dataset.records[2].coordinates == Point(29.0, 6.0)
        assert dataset.events[11].event_type == EventType.MISCONTROL
        assert dataset.events[34].event_type == EventType.INTERCEPTION
        assert dataset.events[143].event_type == EventType.CLEARANCE

        assert (
            dataset.events[39].get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        assert (
            dataset.events[43].get_qualifier_values(DuelQualifier)[1].value
            == DuelType.AERIAL
        )
        assert (
            dataset.events[268].get_qualifier_values(DuelQualifier)[2].value
            == DuelType.SLIDING_TACKLE
        )
        assert (
            dataset.events[301].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )

    def test_correct_auto_recognize_deserialization(self, event_v2_data: Path):
        dataset = wyscout.load(event_data=event_v2_data, coordinates="wyscout")
        assert dataset.records[2].coordinates == Point(29.0, 6.0)
