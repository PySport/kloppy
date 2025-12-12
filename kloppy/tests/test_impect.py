from collections import defaultdict
from datetime import timedelta
from typing import cast

import pytest

from kloppy import impect
from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CarryResult,
    DuelQualifier,
    DuelResult,
    DuelType,
    EventDataset,
    FormationType,
    InterceptionResult,
    Orientation,
    PassResult,
    Point,
    Point3D,
    Provider,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    SubstitutionEvent,
    Time,
)
from kloppy.domain.models import PositionType
from kloppy.domain.models.event import (
    EventType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    PassQualifier,
    PassType,
    UnderPressureQualifier,
)
from kloppy.infra.serializers.event.impect.helpers import parse_timestamp


@pytest.fixture(scope="module")
def dataset(base_dir) -> EventDataset:
    dataset = impect.load(
        event_data=base_dir / "files" / "impect_events.json",
        lineup_data=base_dir / "files" / "impect_lineups.json",
        coordinates="impect",
    )

    return dataset


@pytest.fixture(scope="module")
def dataset_with_names(base_dir) -> EventDataset:
    """Dataset loaded with squad and player names from separate files"""
    dataset = impect.load(
        event_data=base_dir / "files" / "impect_events.json",
        lineup_data=base_dir / "files" / "impect_lineups.json",
        squads_data=base_dir / "files" / "impect_squads.json",
        players_data=base_dir / "files" / "impect_players.json",
        coordinates="impect",
    )

    return dataset


class TestImpectHelpers:
    def test_parse_timestamp(self):
        assert parse_timestamp("00:00.000") == (timedelta(seconds=0), 1)
        assert parse_timestamp("45:00.0000 (+04:16.9200)") == (
            timedelta(minutes=49, seconds=16, microseconds=920000),
            1,
        )
        assert parse_timestamp("45:00.0000") == (timedelta(minutes=0), 2)
        assert parse_timestamp("49:16.9200") == (
            timedelta(minutes=4, seconds=16, microseconds=920000),
            2,
        )
        assert parse_timestamp("90:00.000 (+04:16.9200)") == (
            timedelta(minutes=49, seconds=16, microseconds=920000),
            2,
        )
        assert parse_timestamp("90:00.0000") == (timedelta(minutes=0), 3)
        assert parse_timestamp("99:16.9200") == (
            timedelta(minutes=9, seconds=16, microseconds=919999),
            3,
        )
        assert parse_timestamp("105:00.0000 (+04:16.9200)") == (
            timedelta(minutes=19, seconds=16, microseconds=920000),
            3,
        )
        assert parse_timestamp("109:16.9200") == (
            timedelta(minutes=4, seconds=16, microseconds=920000),
            4,
        )

    def test_period_id_for_all_events(self, dataset):
        for event in dataset.events:
            if event.raw_event:
                period_id = event.raw_event["periodId"]
                timestamp, parsed_period_id = parse_timestamp(
                    event.raw_event["gameTime"]["gameTime"]
                )
                assert (
                    period_id == parsed_period_id
                ), f"Event {event.event_id} has periodId {period_id} but parsed periodId is {parsed_period_id}"


class TestImpectMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the Impect provider"""
        assert dataset.metadata.provider == Provider.IMPECT

    def test_orientation(self, dataset):
        """It should set the action-executing-team orientation"""
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )

    def test_framerate(self, dataset):
        """It should set the frame rate to None"""
        assert dataset.metadata.frame_rate is None

    def test_teams(self, dataset):
        """It should create the teams and player objects"""
        # There should be two teams with the correct names and starting formations
        assert dataset.metadata.teams[0].team_id == "1"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-3-3"
        )
        assert dataset.metadata.teams[1].team_id == "2"
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "5-3-2"
        )

        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("1")
        assert player.player_id == "1"
        assert player.jersey_no == 5
        assert str(player) == "home_5"

    def test_teams_with_names(self, dataset_with_names):
        """It should load team and player names from squads and players files"""
        # Teams should have names loaded
        assert dataset_with_names.metadata.teams[0].team_id == "1"
        assert dataset_with_names.metadata.teams[0].name == "Home Team FC"
        assert dataset_with_names.metadata.teams[1].team_id == "2"
        assert dataset_with_names.metadata.teams[1].name == "Away Team United"

        # Players should have names loaded
        player = dataset_with_names.metadata.teams[0].get_player_by_id("1")
        assert player.player_id == "1"
        assert player.jersey_no == 5
        assert player.name == "John Doe"
        assert str(player) == "John Doe"

        # Check another player
        player2 = dataset_with_names.metadata.teams[0].get_player_by_id("13")
        assert player2.name == "Matthew Anderson"

        # Check away team player
        away_player = dataset_with_names.metadata.teams[1].get_player_by_id(
            "26"
        )
        assert away_player.name == "Ronald Clark"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        # Starting players get their position from the STARTING_XI event
        player = dataset.metadata.teams[0].get_player_by_id("5")

        assert player.starting_position == PositionType.RightCentralMidfield
        assert player.starting

        # Substituted players have a position
        sub_player = dataset.metadata.teams[0].get_player_by_id("1")
        assert sub_player.starting_position is None
        assert sub_player.positions.last() is not None
        assert not sub_player.starting

        # Get player by position and time
        periods = dataset.metadata.periods
        period_1 = periods[0]
        period_2 = periods[1]

        home_starting_gk = dataset.metadata.teams[0].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_gk.player_id == "13"
        assert home_starting_gk.jersey_no == 30

        home_starting_lwb = dataset.metadata.teams[0].get_player_by_position(
            PositionType.LeftWingBack,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_lwb.player_id == "15"

        home_ending_lwb = dataset.metadata.teams[0].get_player_by_position(
            PositionType.LeftWingBack,
            time=Time(period=period_2, timestamp=timedelta(seconds=45 * 60)),
        )
        assert home_ending_lwb.player_id == "12"

        away_starting_gk = dataset.metadata.teams[1].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=92)),
        )
        assert away_starting_gk.player_id == "26"

    def test_periods(self, dataset):
        """It should create the periods with correct cumulative timestamps"""
        assert len(dataset.metadata.periods) == 2

        # Period 1 assertions
        period_1 = dataset.metadata.periods[0]
        assert period_1.id == 1
        assert period_1.start_timestamp == timedelta(
            seconds=0
        )  # Should start at 0
        assert period_1.end_timestamp is not None
        assert period_1.end_timestamp > period_1.start_timestamp

        # Period 2 assertions
        period_2 = dataset.metadata.periods[1]
        assert period_2.id == 2
        assert (
            period_2.start_timestamp == period_1.end_timestamp
        )  # Should start where period 1 ended
        assert period_2.end_timestamp is not None
        assert period_2.end_timestamp > period_2.start_timestamp

        # Verify cumulative nature: period 2 should start after period 1 ends
        assert period_2.start_timestamp > period_1.start_timestamp
        assert period_2.end_timestamp > period_1.end_timestamp

        # Verify reasonable duration (each period should be around 45+ minutes)
        period_1_duration = period_1.end_timestamp - period_1.start_timestamp
        period_2_duration = period_2.end_timestamp - period_2.start_timestamp

        assert period_1_duration >= timedelta(
            minutes=45
        )  # At least 45 minutes
        assert period_1_duration <= timedelta(
            minutes=60
        )  # At most 60 minutes (allows for extra time)
        assert period_2_duration >= timedelta(
            minutes=45
        )  # At least 45 minutes
        assert period_2_duration <= timedelta(
            minutes=100
        )  # At most 100 minutes (allows for extra time)


class TestImpectEvent:
    """Generic tests related to deserializing events"""

    def test_unique_event_ids(self, dataset: EventDataset):
        """It should create unique event ids"""
        event_ids = defaultdict(int)
        for event in dataset.events:
            event_ids[event.event_id] += 1
        assert all(
            v == 1 for v in event_ids.values()
        ), "Event IDs are not unique"

    def test_generic_attributes(self, dataset: EventDataset):
        """Test generic event attributes"""
        event = dataset.get_event_by_id("1")
        assert event.event_id == "1"
        assert event.team.team_id == "1"
        assert event.ball_owning_team.team_id == "1"
        assert event.player.full_name == "home_9"
        assert event.coordinates == Point(x=0.0, y=0.0)
        assert event.raw_event["id"] == 1
        assert event.period.id == 1
        assert event.timestamp == timedelta(seconds=0)
        assert event.ball_state == BallState.ALIVE

    def test_timestamp(self, dataset):
        """It should set the correct timestamp, reset to zero after each period"""
        kick_offs = [
            e
            for e in dataset.events
            if e.event_type == EventType.PASS
            and e.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        ]
        kickoff_p1 = kick_offs[0]
        assert kickoff_p1.timestamp == timedelta(seconds=0)
        kick_off_p2 = kick_offs[1]
        assert kick_off_p2.timestamp == timedelta(seconds=0)

        # Verify that kickoffs are in different periods but both start at 0
        assert kickoff_p1.period.id == 1
        assert kick_off_p2.period.id == 2
        assert (
            kickoff_p1.timestamp == kick_off_p2.timestamp
        )  # Both should be 0

        # Verify that events within each period have timestamps relative to that period
        period_1_events = [e for e in dataset.events if e.period.id == 1]
        period_2_events = [e for e in dataset.events if e.period.id == 2]

        # First event in each period should be close to 0
        assert period_1_events[0].timestamp <= timedelta(seconds=1)
        assert period_2_events[0].timestamp <= timedelta(seconds=1)

        # Events should be in chronological order within each period
        for i in range(
            1, min(10, len(period_1_events))
        ):  # Check first 10 events
            assert (
                period_1_events[i].timestamp
                >= period_1_events[i - 1].timestamp
            )
        for i in range(
            1, min(10, len(period_2_events))
        ):  # Check first 10 events
            assert (
                period_2_events[i].timestamp
                >= period_2_events[i - 1].timestamp
            )


class TestImpectPassEvent:
    """Tests related to deserialzing pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all pass events"""
        events = dataset.find_all("pass")
        assert len(events) == 1110

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play pass"""
        pass_event = dataset.get_event_by_id("4")
        # A pass should have a result
        assert pass_event.result == PassResult.COMPLETE
        # A pass should have end coordinates
        assert pass_event.receiver_coordinates == Point(x=-20.9, y=16.7)
        # A pass should have an end timestamp
        assert pass_event.receive_timestamp == timedelta(
            seconds=3, microseconds=668000
        )
        # A pass should have a receiver
        assert pass_event.receiver_player.player_id == "15"
        # A pass should have a body part
        assert (
            pass_event.get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )
        # A pass can have set piece qualifiers
        assert pass_event.get_qualifier_value(SetPieceQualifier) is None
        # A pass can have pass qualifiers
        assert pass_event.get_qualifier_value(PassQualifier) is None

    def test_set_piece(self, dataset: EventDataset):
        """It should add set piece qualifiers to free kick passes"""
        pass_event = dataset.get_event_by_id("98")
        assert (
            pass_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.FREE_KICK
        )

    def test_assists(self, dataset: EventDataset):
        shot_assists = [
            e
            for e in dataset.events
            if e.event_type == EventType.PASS
            and PassType.SHOT_ASSIST in e.get_qualifier_values(PassQualifier)
        ]
        assert len(shot_assists) == 8

        goal_assists = [
            e
            for e in dataset.events
            if e.event_type == EventType.PASS
            and PassType.ASSIST in e.get_qualifier_values(PassQualifier)
        ]
        assert len(goal_assists) == 3


class TestImpectInterceptionEvent:
    """Tests related to deserialzing pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("interception")
        assert len(events) == 52

    def test_interception(self, dataset: EventDataset):
        """It should split interception passes into two events"""
        interception = dataset.get_event_by_id("41")
        assert interception.event_type == EventType.INTERCEPTION
        assert interception.result == InterceptionResult.SUCCESS


class TestImpectShotEvent:
    """Tests related to deserialzing 16/Shot events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("shot")
        assert len(events) == 22

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play shot"""
        shot = dataset.get_event_by_id("620")
        # A shot event should have a result
        assert shot.result == ShotResult.GOAL
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(
            x=100, y=2.793322932917317, z=0.540161290322581
        )
        # A shot event should have a body part
        assert (
            shot.get_qualifier_value(BodyPartQualifier) == BodyPart.RIGHT_FOOT
        )
        # An open play shot should not have a set piece qualifier
        assert shot.get_qualifier_value(SetPieceQualifier) is None


class TestImpectClearanceEvent:
    """Tests related to deserializing 9/Clearance events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 54

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of clearances"""
        clearance = dataset.get_event_by_id("42")
        # A clearance has no result
        assert clearance.result is None
        assert (
            clearance.get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )


class TestImpectCarryEvent:
    """Tests related to deserializing 22/Carry events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all carry events"""
        events = dataset.find_all("carry")
        assert len(events) == 742

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of carries"""
        carry = dataset.get_event_by_id("3")
        # A carry is always successful
        assert carry.result == CarryResult.COMPLETE
        # A carry should have an end location
        assert carry.end_coordinates == Point(x=-12.2, y=4.9)
        # A carry should have an end timestamp
        assert carry.timestamp == timedelta(microseconds=685100)
        assert carry.end_timestamp == timedelta(seconds=1, microseconds=754000)


class TestImpectDuelEvent:
    """Tests related to deserializing 1/Duel events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all duel and 50/50 events"""
        events = dataset.find_all("duel")
        assert len(events) == 130

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of duels"""
        duel = dataset.get_event_by_id("45")
        # A duel should have a result
        assert duel.result == DuelResult.WON
        # A duel should have a duel type
        assert duel.get_qualifier_values(DuelQualifier) == [DuelType.GROUND]
        # A duel does not have a body part
        assert duel.get_qualifier_value(BodyPartQualifier) == BodyPart.OTHER

        # it should create an artificial duel lost event for the opponent
        lost_duel = dataset.get_event_by_id("37-ground-duel-45")
        # A duel should have a result
        assert lost_duel.result == DuelResult.LOST
        # A duel should have a duel type
        assert lost_duel.get_qualifier_values(DuelQualifier) == [
            DuelType.GROUND
        ]
        # A duel does not have a body part
        assert duel.get_qualifier_value(BodyPartQualifier) == BodyPart.OTHER

    def test_aerial_duel(self, dataset: EventDataset):
        duel = dataset.get_event_by_id("15-aerial-duel-135")
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.LOOSE_BALL,
            DuelType.AERIAL,
        ]


class TestImpectGoalkeeperEvent:
    """Tests related to deserializing 30/Goalkeeper events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all goalkeeper events"""
        events = dataset.find_all("goalkeeper")
        assert len(events) == 17

    def test_save(self, dataset: EventDataset):
        """It should deserialize goalkeeper saves"""
        # A save should be deserialized as a goalkeeper event
        save = dataset.get_event_by_id("1137")
        assert save.get_qualifier_value(GoalkeeperQualifier) == (
            GoalkeeperActionType.SAVE
        )

    def test_catch(self, dataset: EventDataset):
        """It should deserialize goalkeeper catch"""
        collected = dataset.get_event_by_id("187")
        assert collected.get_qualifier_value(GoalkeeperQualifier) == (
            GoalkeeperActionType.CLAIM
        )


class TestImpectSubstitutionEvent:
    """Tests related to deserializing 18/Substitution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all substitution events"""
        events = dataset.find_all("substitution")
        assert len(events) == 7

        # Verify that the player and replacement player are set correctly
        # Note: events are sorted when inserted, so order may differ from creation order
        subs = [
            ("15", "1"),
            ("2", "11"),  # 60:00 OUT -> 60:15 IN (15 second gap)
            ("4", "6"),
            # Player 10 at 75:00 had red card - skipped
            ("31", "29"),
            ("38", "32"),  # At 79:59: events get reordered after insertion
            ("37", "28"),  # At 79:59: events get reordered after insertion
            ("7", "12"),
        ]
        for event_idx, (player_id, replacement_player_id) in enumerate(subs):
            event = cast(SubstitutionEvent, events[event_idx])
            assert event.player == event.team.get_player_by_id(player_id)
            assert event.replacement_player == event.team.get_player_by_id(
                replacement_player_id
            )

    def test_player_off_without_replacement(self, dataset: EventDataset):
        """It should create PlayerOff event when player goes out without replacement"""
        # Player 14 goes OUT at 85:00 with no matching IN (added to test data)
        player_off_events = dataset.find_all("player_off")

        assert (
            len(player_off_events) >= 1
        ), "Should have at least one PlayerOff event"

        # Find PlayerOff event for player 14
        player_14_offs = [
            e for e in player_off_events if e.player.player_id == "14"
        ]
        assert (
            len(player_14_offs) == 1
        ), "Player 14 should have exactly one PlayerOff event"

        player_off = player_14_offs[0]
        assert player_off.player.player_id == "14"
        assert player_off.team == dataset.metadata.teams[0]  # Home team
        assert player_off.period.id == 2  # Second period
        assert player_off.timestamp == timedelta(
            minutes=40, seconds=0
        )  # 85:00 - 45:00


class TestImpectFoulCommittedEvent:
    """Tests related to deserializing 2/Foul Committed events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all foul committed events"""
        events = dataset.find_all("foul_committed")
        assert len(events) == 13


class TestImpectRecoveryEvent:
    """Tests related to deserializing 23/Recovery events"""

    def test_deserialize_recoveries(self, dataset: EventDataset):
        events = dataset.find_all("recovery")
        assert len(events) == 156


class TestImpectUnderPressureQualifier:
    """Tests related to deserializing pressure data"""

    def test_under_pressure(self, dataset: EventDataset):
        """It should add the under pressure qualifier when pressure > 0"""
        # Event 2 has pressure = 75
        under_pressure = dataset.get_event_by_id("3")
        assert under_pressure.get_qualifier_value(UnderPressureQualifier)

        # Event 1 has pressure = null
        no_pressure = dataset.get_event_by_id("1")
        assert no_pressure.get_qualifier_value(UnderPressureQualifier) is None
