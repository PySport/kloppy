from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy import wyscout
from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    DatasetType,
    DuelQualifier,
    DuelType,
    EventDataset,
    EventType,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    Orientation,
    PassQualifier,
    PassResult,
    PassType,
    Point,
    PositionType,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    Time,
)


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
    assert dataset.records[2].coordinates == Point(32.0, 56.0)


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

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "2499773"

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
        assert dataset.records[2].coordinates == Point(
            0.2981354967264447, 0.06427244582043344
        )


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
            minutes=45, seconds=5
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            minutes=45, seconds=5
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            minutes=45, seconds=5
        ) + timedelta(minutes=46, seconds=53)

        assert (
            dataset.metadata.teams[0].starting_formation
            == FormationType.THREE_FOUR_TWO_ONE
        )

        formation_time_change = Time(
            dataset.metadata.periods[1], timedelta(seconds=3)
        )
        assert (
            dataset.metadata.teams[1].formations.items[formation_time_change]
            == FormationType.FOUR_THREE_ONE_TWO
        )

        cr7 = dataset.metadata.teams[0].get_player_by_id("3322")

        assert cr7.full_name == "Cristiano Ronaldo dos Santos Aveiro"
        assert cr7.starting is True
        assert cr7.positions.last() == PositionType.Striker

    def test_enriched_metadata(self, dataset: EventDataset):
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(2020, 9, 20, 18, 45, tzinfo=timezone.utc)

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "1"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "5154199"

    def test_timestamps(self, dataset: EventDataset):
        kickoff_p1 = dataset.get_event_by_id(1927028854)
        assert kickoff_p1.timestamp == timedelta(minutes=0, seconds=3)
        kickoff_p2 = dataset.get_event_by_id(1927029460)
        assert kickoff_p2.timestamp == timedelta(minutes=0, seconds=0)

    def test_coordinates(self, dataset: EventDataset):
        assert dataset.records[2].coordinates == Point(32.0, 56.0)

    def test_normalized_deserialization(self, event_v3_data: Path):
        dataset = wyscout.load(event_data=event_v3_data, data_version="V3")
        assert dataset.records[2].coordinates == Point(
            x=0.32643853442316295, y=0.5538235294117646
        )

    def test_pass_event(self, dataset: EventDataset):
        pass_event = dataset.get_event_by_id(1927028486)
        assert pass_event.event_type == EventType.PASS
        assert pass_event.coordinates == Point(x=22.0, y=91.0)
        assert pass_event.receiver_coordinates == Point(x=8.0, y=71.0)

        blocked_pass_event = dataset.get_event_by_id(1927029452)
        assert blocked_pass_event.result == PassResult.INCOMPLETE
        assert blocked_pass_event.coordinates == Point(x=96.0, y=85.0)
        assert blocked_pass_event.receiver_coordinates == Point(x=99.0, y=84.0)

    def test_goalkeeper_event(self, dataset: EventDataset):
        goalkeeper_event = dataset.get_event_by_id(1927029095)
        assert goalkeeper_event.event_type == EventType.GOALKEEPER
        assert (
            goalkeeper_event.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )

    def test_shot_assist_event(self, dataset: EventDataset):
        shot_assist_event = dataset.get_event_by_id(1927028561)
        assert shot_assist_event.event_type == EventType.PASS
        assert PassType.SHOT_ASSIST in shot_assist_event.get_qualifier_values(
            PassQualifier
        )

    def test_shot_event(self, dataset: EventDataset):
        # a blocked free kick shot
        blocked_shot_event = dataset.get_event_by_id(1927028534)
        assert blocked_shot_event.event_type == EventType.SHOT
        assert blocked_shot_event.result == ShotResult.BLOCKED
        assert blocked_shot_event.result_coordinates == Point(x=77.0, y=21.0)
        assert (
            blocked_shot_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.FREE_KICK
        )
        # off target shot
        off_target_shot = dataset.get_event_by_id(1927028562)
        assert off_target_shot.event_type == EventType.SHOT
        assert off_target_shot.result == ShotResult.OFF_TARGET
        assert off_target_shot.result_coordinates is None
        # on target shot
        on_target_shot = dataset.get_event_by_id(1927028637)
        assert on_target_shot.event_type == EventType.SHOT
        assert on_target_shot.result == ShotResult.SAVED
        assert on_target_shot.result_coordinates == Point(100.0, 45.0)

    def test_foul_committed_event(self, dataset: EventDataset):
        foul_committed_event = dataset.get_event_by_id(1927028873)
        assert foul_committed_event.event_type == EventType.FOUL_COMMITTED

    def test_duel_event(self, dataset: EventDataset):
        ground_duel_event = dataset.get_event_by_id(1927028474)
        assert ground_duel_event.event_type == EventType.DUEL
        assert (
            ground_duel_event.get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        aerial_loose_ball_duel_event = dataset.get_event_by_id(1927028472)
        assert aerial_loose_ball_duel_event.event_type == EventType.DUEL
        assert (
            DuelType.LOOSE_BALL
            in aerial_loose_ball_duel_event.get_qualifier_values(DuelQualifier)
        )
        assert (
            DuelType.AERIAL
            in aerial_loose_ball_duel_event.get_qualifier_values(DuelQualifier)
        )
        sliding_tackle_duel_event = dataset.get_event_by_id(1927028828)
        assert sliding_tackle_duel_event.event_type == EventType.DUEL
        assert (
            DuelType.SLIDING_TACKLE
            in sliding_tackle_duel_event.get_qualifier_values(DuelQualifier)
        )

    def test_clearance_event(self, dataset: EventDataset):
        clearance_event = dataset.get_event_by_id(1927028482)
        assert clearance_event.event_type == EventType.CLEARANCE

    def test_interception_event(self, dataset: EventDataset):
        interception_event = dataset.get_event_by_id(1927028880)
        assert interception_event.event_type == EventType.INTERCEPTION

    def test_take_on_event(self, dataset: EventDataset):
        take_on_event = dataset.get_event_by_id(1927028870)
        assert take_on_event.event_type == EventType.TAKE_ON

    def test_carry_event(self, dataset: EventDataset):
        carry_event = dataset.get_event_by_id(1927028490)
        assert carry_event.event_type == EventType.CARRY
        assert carry_event.end_coordinates == Point(17.0, 4.0)
