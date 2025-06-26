from collections import defaultdict
from datetime import timedelta
from typing import cast

import pytest

from kloppy import korastats
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
)


@pytest.fixture(scope="module")
def dataset(base_dir) -> EventDataset:
    dataset = korastats.load(
        event_data=base_dir / "files" / "korastats_events.json",
        squads_data=base_dir / "files" / "korastats_squads.json",
        coordinates="korastats",
    )

    return dataset


class TestKoraStatsMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the KoraStats provider"""
        assert dataset.metadata.provider == Provider.KORASTATS

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
        assert dataset.metadata.teams[0].team_id == "10107"
        # assert dataset.metadata.teams[0].starting_formation == FormationType(
        #     "4-3-3"
        # )
        assert dataset.metadata.teams[1].team_id == "23109"
        # assert dataset.metadata.teams[1].starting_formation == FormationType(
        #     "5-3-2"
        # )

        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("194622")
        assert player.player_id == "194622"
        assert player.jersey_no == 1
        assert str(player) == "Samuel Erik Oskar Brolin"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        player = dataset.metadata.teams[0].get_player_by_id("194622")

        assert player.starting_position == PositionType.Goalkeeper
        assert player.starting

        # Substituted players have a position
        sub_player = dataset.metadata.teams[0].get_player_by_id("436613")
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
        assert home_starting_gk.player_id == "194622"
        assert home_starting_gk.jersey_no == 1

        home_starting_rcb = dataset.metadata.teams[0].get_player_by_position(
            PositionType.CenterMidfield,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_rcb.player_id == "195863"

        home_ending_rcb = dataset.metadata.teams[0].get_player_by_position(
            PositionType.CenterMidfield,
            time=Time(period=period_2, timestamp=timedelta(seconds=45 * 60)),
        )
        assert home_ending_rcb.player_id == "436613"

        away_starting_gk = dataset.metadata.teams[1].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=92)),
        )
        assert away_starting_gk.player_id == "436614"

    def test_periods(self, dataset):
        """It should create the periods"""
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1


class TestKoraStatsEvent:
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
        event = dataset.get_event_by_id("144880351")
        assert event.event_id == "144880351"
        assert event.team.team_id == "10107"
        # assert event.ball_owning_team.team_id == '10107'
        assert event.player.full_name == "Gibril Sosseh"
        assert event.coordinates == Point(x=50, y=50)
        assert event.raw_event["_id"] == 144880351
        assert event.period.id == 1
        assert event.timestamp == timedelta(microseconds=467000)
        # assert event.ball_state == BallState.ALIVE

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
        assert kickoff_p1.timestamp == timedelta(microseconds=467000)
        kick_off_p2 = kick_offs[1]
        assert kick_off_p2.timestamp == timedelta(microseconds=427000)


class TestKoraStatsPassEvent:
    """Tests related to deserialzing pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all pass events"""
        events = dataset.find_all("pass")
        assert len(events) == 869

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play pass"""
        pass_event = dataset.get_event_by_id("144880455")
        # A pass should have a result
        assert pass_event.result == PassResult.COMPLETE
        # A pass should have end coordinates
        assert pass_event.coordinates == Point(x=20, y=62)
        assert pass_event.receiver_coordinates == Point(x=8, y=59)
        # A pass should have an end timestamp
        assert pass_event.timestamp == timedelta(
            seconds=21, microseconds=181000
        )
        assert pass_event.receive_timestamp == timedelta(
            seconds=25, microseconds=85000
        )
        # A pass should have a receiver
        assert pass_event.receiver_player.player_id == "436614"
        # A pass can have set piece qualifiers
        assert pass_event.get_qualifier_value(SetPieceQualifier) is None
        # A pass can have pass qualifiers
        assert pass_event.get_qualifier_value(PassQualifier) is None

    def test_set_pieces(self, dataset: EventDataset):
        """It should add set piece qualifiers to free kick passes"""
        assert (
            len(
                [
                    e
                    for e in dataset.events
                    if e.get_qualifier_value(SetPieceQualifier)
                    == SetPieceType.FREE_KICK
                ]
            )
            == 22
        )

    # def test_assists(self, dataset: EventDataset):
    #     shot_assists = [
    #         e
    #         for e in dataset.events
    #         if PassType.SHOT_ASSIST in e.get_qualifier_values(PassQualifier)
    #     ]
    #     assert len(shot_assists) == 8
    #
    #     goal_assists = [
    #         e
    #         for e in dataset.events
    #         if PassType.ASSIST in e.get_qualifier_values(PassQualifier)
    #     ]
    #     assert len(goal_assists) == 3


class TestKoraStatsInterceptionEvent:
    """Tests related to deserialzing pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("interception")
        assert len(events) == 100

    def test_interception(self, dataset: EventDataset):
        """It should split interception passes into two events"""
        interception = dataset.get_event_by_id("144880413")
        assert interception.event_type == EventType.INTERCEPTION
        assert interception.result == InterceptionResult.SUCCESS


class TestKoraStatsShotEvent:
    """Tests related to deserialzing 16/Shot events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("shot")
        assert len(events) == 20

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play shot"""
        shot = dataset.get_event_by_id("144881556")
        # A shot event should have a result
        assert shot.result == ShotResult.GOAL
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(
            x=100, y=-2.9842666666666666, z=1.5046666666666666
        )
        # A shot event should have a body part
        assert (
            shot.get_qualifier_value(BodyPartQualifier) == BodyPart.RIGHT_FOOT
        )
        # An open play shot should not have a set piece qualifier
        assert shot.get_qualifier_value(SetPieceQualifier) is None


class TestKoraStatsClearanceEvent:
    """Tests related to deserializing 9/Clearance events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 10

    # def test_attributes(self, dataset: EventDataset):
    #     """Verify specific attributes of clearances"""
    #     clearance = dataset.get_event_by_id("42")
    #     # A clearance has no result
    #     assert clearance.result is None
    #     assert (
    #             clearance.get_qualifier_value(BodyPartQualifier)
    #             == BodyPart.RIGHT_FOOT
    #     )


class TestKoraStatsDuelEvent:
    """Tests related to deserializing 1/Duel events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all duel and 50/50 events"""
        events = dataset.find_all("duel")
        assert len(events) == 100

    # def test_attributes(self, dataset: EventDataset):
    #     """Verify specific attributes of duels"""
    #     duel = dataset.get_event_by_id("45")
    #     # A duel should have a result
    #     assert duel.result == DuelResult.WON
    #     # A duel should have a duel type
    #     assert duel.get_qualifier_values(DuelQualifier) == [DuelType.GROUND]
    #     # A duel does not have a body part
    #     assert duel.get_qualifier_value(BodyPartQualifier) == BodyPart.OTHER
    #
    #     # it should create an artificial duel lost event for the opponent
    #     lost_duel = dataset.get_event_by_id("37-ground-duel-45")
    #     # A duel should have a result
    #     assert lost_duel.result == DuelResult.LOST
    #     # A duel should have a duel type
    #     assert lost_duel.get_qualifier_values(DuelQualifier) == [
    #         DuelType.GROUND
    #     ]
    #     # A duel does not have a body part
    #     assert duel.get_qualifier_value(BodyPartQualifier) == BodyPart.OTHER

    # def test_aerial_duel(self, dataset: EventDataset):
    #     duel = dataset.get_event_by_id("15-aerial-duel-135")
    #     assert duel.get_qualifier_values(DuelQualifier) == [
    #         DuelType.LOOSE_BALL,
    #         DuelType.AERIAL,
    #     ]


class TestKoraStatsGoalkeeperEvent:
    """Tests related to deserializing 30/Goalkeeper events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all goalkeeper events"""
        events = dataset.find_all("goalkeeper")
        assert len(events) == 15

    # def test_save(self, dataset: EventDataset):
    #     """It should deserialize goalkeeper saves"""
    #     # A save should be deserialized as a goalkeeper event
    #     save = dataset.get_event_by_id("1137")
    #     assert save.get_qualifier_value(GoalkeeperQualifier) == (
    #         GoalkeeperActionType.SAVE
    #     )
    #
    # def test_catch(self, dataset: EventDataset):
    #     """It should deserialize goalkeeper catch"""
    #     collected = dataset.get_event_by_id("187")
    #     assert collected.get_qualifier_value(GoalkeeperQualifier) == (
    #         GoalkeeperActionType.CLAIM
    #     )


class TestKoraStatsSubstitutionEvent:
    """Tests related to deserializing 18/Substitution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all substitution events"""
        events = dataset.find_all("substitution")
        assert len(events) == 8

        # Verify that the player and replacement player are set correctly
        # subs = [
        #     ("15", "1"),
        #     ("4", "6"),
        #     ("31", "29"),
        #     ("38", "32"),
        #     ("37", "28"),
        #     ("7", "12"),
        # ]
        # for event_idx, (player_id, replacement_player_id) in enumerate(subs):
        #     event = cast(SubstitutionEvent, events[event_idx])
        #     assert event.player == event.team.get_player_by_id(player_id)
        #     assert event.replacement_player == event.team.get_player_by_id(
        #         replacement_player_id
        #     )


class TestKoraStatsFoulCommittedEvent:
    """Tests related to deserializing 2/Foul Committed events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all foul committed events"""
        events = dataset.find_all("foul_committed")
        assert len(events) == 36


class TestKoraStatsRecoveryEvent:
    """Tests related to deserializing 23/Recovery events"""

    def test_deserialize_recoveries(self, dataset: EventDataset):
        events = dataset.find_all("recovery")
        assert len(events) == 157
