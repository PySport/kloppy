from datetime import datetime, timedelta
from pathlib import Path

import pytest
from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    Point,
    EventDataset,
    SetPieceType,
    SetPieceQualifier,
    DatasetType,
    DuelQualifier,
    DuelType,
    EventType,
    GoalkeeperQualifier,
    GoalkeeperActionType,
    CardQualifier,
    CardType,
    Orientation,
)

from kloppy import wyscout


@pytest.fixture(scope="session")
def event_v2_data(base_dir: Path) -> Path:
    return base_dir / "files" / "wyscout_events_v2.json"


@pytest.fixture(scope="session")
def event_v3_data(base_dir: Path) -> Path:
    return base_dir / "files" / "wyscout_events_v3.json"


def test_correct_auto_recognize_deserialization(
    event_v2_data: Path, event_v3_data: Path
):
    dataset = wyscout.load(event_data=event_v2_data, coordinates="wyscout")
    assert dataset.records[2].coordinates == Point(29.0, 6.0)
    dataset = wyscout.load(event_data=event_v3_data, coordinates="wyscout")
    assert dataset.records[2].coordinates == Point(36.0, 78.0)


class TestWyscoutV2:
    """Tests related to deserialization of Wyscout V2 data."""

    @pytest.fixture(scope="class")
    def dataset(self, event_v2_data) -> EventDataset:
        """Load Wyscout V2 event dataset"""
        dataset = wyscout.load(
            event_data=event_v2_data,
            coordinates="wyscout",
            data_version="V2",
        )
        assert dataset.dataset_type == DatasetType.EVENT
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        return dataset

    def test_metadata(self, dataset: EventDataset):
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=2863.708369
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=2863.708369
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=2863.708369
        ) + timedelta(seconds=2999.70982)

    def test_timestamps(self, dataset: EventDataset):
        kickoff_p1 = dataset.get_event_by_id("190078343")
        assert kickoff_p1.timestamp == timedelta(seconds=2.643377)
        kickoff_p2 = dataset.get_event_by_id("190079822")
        assert kickoff_p2.timestamp == timedelta(seconds=0)

    def test_shot_event(self, dataset: EventDataset):
        shot_event = dataset.get_event_by_id("190079151")
        assert (
            shot_event.get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )

    def test_miscontrol_event(self, dataset: EventDataset):
        miscontrol_event = dataset.get_event_by_id("190078351")
        assert miscontrol_event.event_type == EventType.MISCONTROL

    def test_interception_event(self, dataset: EventDataset):
        # A touch or duel with "interception" tag should be converted to an interception event
        interception_event = dataset.get_event_by_id("190079090")
        assert interception_event.event_type == EventType.INTERCEPTION
        # Other events with "interception" tag should be split in two events
        clearance_event = dataset.get_event_by_id("190079171")
        assert clearance_event.event_type == EventType.CLEARANCE
        interception_event = dataset.get_event_by_id("interception-190079171")
        assert interception_event.event_type == EventType.INTERCEPTION

    def test_duel_event(self, dataset: EventDataset):
        ground_duel_event = dataset.get_event_by_id("190078379")
        assert ground_duel_event.event_type == EventType.DUEL
        assert (
            ground_duel_event.get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        aerial_duel_event = dataset.get_event_by_id("190078381")
        assert aerial_duel_event.event_type == EventType.DUEL
        assert (
            aerial_duel_event.get_qualifier_values(DuelQualifier)[1]
            == DuelType.AERIAL
        )
        sliding_tackle_duel_event = dataset.get_event_by_id("190079260")
        assert sliding_tackle_duel_event.event_type == EventType.DUEL
        assert (
            sliding_tackle_duel_event.get_qualifier_values(DuelQualifier)[2]
            == DuelType.SLIDING_TACKLE
        )

    def test_goalkeeper_event(self, dataset: EventDataset):
        goalkeeper_event = dataset.get_event_by_id("190079010")
        assert goalkeeper_event.event_type == EventType.GOALKEEPER
        assert (
            goalkeeper_event.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )

    def test_foul_committed_event(self, dataset: EventDataset):
        foul_committed_event = dataset.get_event_by_id("190079289")
        assert foul_committed_event.event_type == EventType.FOUL_COMMITTED
        assert (
            foul_committed_event.get_qualifier_value(CardQualifier)
            == CardType.FIRST_YELLOW
        )
        card_event = dataset.get_event_by_id("card-190079289")
        assert card_event.event_type == EventType.CARD

    def test_correct_normalized_deserialization(self, event_v2_data: Path):
        dataset = wyscout.load(event_data=event_v2_data, data_version="V2")
        assert dataset.records[2].coordinates == Point(0.29, 0.06)


class TestWyscoutV3:
    """Tests related to deserialization of Wyscout V3 data."""

    @pytest.fixture(scope="class")
    def dataset(self, event_v3_data: Path) -> EventDataset:
        """Load Wyscout V3 event dataset"""
        dataset = wyscout.load(
            event_data=event_v3_data,
            coordinates="wyscout",
            data_version="V3",
        )
        assert dataset.dataset_type == DatasetType.EVENT
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        return dataset

    def test_metadata(self, dataset: EventDataset):
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            minutes=20, seconds=47
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            minutes=20, seconds=47
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            minutes=20, seconds=47
        ) + timedelta(minutes=50, seconds=30)

    def test_timestamps(self, dataset: EventDataset):
        kickoff_p1 = dataset.get_event_by_id(663292348)
        assert kickoff_p1.timestamp == timedelta(minutes=0, seconds=1)
        # Note: the test file is incorrect. The second period start at 45:00
        kickoff_p2 = dataset.get_event_by_id(1331979498)
        assert kickoff_p2.timestamp == timedelta(
            minutes=1, seconds=0
        ) - timedelta(minutes=45)

    def test_coordinates(self, dataset: EventDataset):
        assert dataset.records[2].coordinates == Point(36.0, 78.0)

    def test_normalized_deserialization(self, event_v3_data: Path):
        dataset = wyscout.load(event_data=event_v3_data, data_version="V3")
        assert dataset.records[2].coordinates == Point(0.36, 0.78)

    def test_goalkeeper_event(self, dataset: EventDataset):
        goalkeeper_event = dataset.get_event_by_id(1331979498)
        assert goalkeeper_event.event_type == EventType.GOALKEEPER
        assert (
            goalkeeper_event.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )

    def test_shot_event(self, dataset: EventDataset):
        shot_event = dataset.get_event_by_id(663291840)
        assert shot_event.event_type == EventType.SHOT
        assert (
            shot_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.CORNER_KICK
        )

    def test_foul_committed_event(self, dataset: EventDataset):
        foul_committed_event = dataset.get_event_by_id(1343788476)
        assert foul_committed_event.event_type == EventType.FOUL_COMMITTED

    def test_duel_event(self, dataset: EventDataset):
        ground_duel_event = dataset.get_event_by_id(663291421)
        assert ground_duel_event.event_type == EventType.DUEL
        assert (
            ground_duel_event.get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        aerial_duel_event = dataset.get_event_by_id(663291841)
        assert aerial_duel_event.event_type == EventType.DUEL
        assert (
            aerial_duel_event.get_qualifier_values(DuelQualifier)[1]
            == DuelType.AERIAL
        )
        sliding_tackle_duel_event = dataset.get_event_by_id(663291842)
        assert sliding_tackle_duel_event.event_type == EventType.DUEL
        assert (
            sliding_tackle_duel_event.get_qualifier_values(DuelQualifier)[2]
            == DuelType.SLIDING_TACKLE
        )

    def test_clearance_event(self, dataset: EventDataset):
        clearance_event = dataset.get_event_by_id(663291843)
        assert clearance_event.event_type == EventType.CLEARANCE

    def test_interception_event(self, dataset: EventDataset):
        interception_event = dataset.get_event_by_id(1397082780)
        assert interception_event.event_type == EventType.INTERCEPTION

    def test_take_on_event(self, dataset: EventDataset):
        take_on_event = dataset.get_event_by_id(139800000)
        assert take_on_event.event_type == EventType.TAKE_ON
