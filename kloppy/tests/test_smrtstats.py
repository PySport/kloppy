from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from kloppy import smrtstats
from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CarryResult,
    DatasetFlag,
    DatasetType,
    Dimension,
    DuelQualifier,
    DuelResult,
    DuelType,
    EventDataset,
    FormationType,
    ImperialPitchDimensions,
    InterceptionResult,
    Orientation,
    PassResult,
    Point,
    Point3D,
    PositionType,
    Provider,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    SubstitutionEvent,
    TakeOnResult,
    Time,
    build_coordinate_system,
    MetricPitchDimensions,
)
from kloppy.domain.models import PositionType
from kloppy.domain.models.event import (
    CardType,
    CounterAttackQualifier,
    EventType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    PassQualifier,
    PassType,
    UnderPressureQualifier,
)
from kloppy.exceptions import DeserializationError


@pytest.fixture(scope="module")
def dataset(base_dir) -> EventDataset:
    """Load SmrtStats data for Belgium - Portugal at Euro 2020"""
    dataset = smrtstats.load(
        raw_data=base_dir / "files" / "smrtstats.json",
        coordinates="smrtstats",
    )
    assert dataset.dataset_type == DatasetType.EVENT
    return dataset


class TestSmrtStatsMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the SmrtStats provider"""
        assert dataset.metadata.provider == Provider.SMRTSTATS

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
        assert dataset.metadata.teams[0].name == "Orange County SC"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-1-4-1"
        )
        assert dataset.metadata.teams[1].name == "New Mexico United"
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-1-4-1"
        )
        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("54824")
        assert player.player_id == "54824"
        assert player.jersey_no == 5
        assert str(player) == "Tom Patrizio Brewitt"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        player = dataset.metadata.teams[0].get_player_by_id("54824")

        assert player.starting_position == PositionType.RightCenterBack
        assert player.starting

        # Substituted players have a position
        sub_player = dataset.metadata.teams[0].get_player_by_id("421305")
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
        assert home_starting_gk.player_id == "228262"  # Colin Shutler

        home_starting_lam = dataset.metadata.teams[0].get_player_by_position(
            PositionType.RightMidfield,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_lam.player_id == "181"  # Cameron Gatlin Dunbar

        home_ending_lam = dataset.metadata.teams[0].get_player_by_position(
            PositionType.RightMidfield,
            time=Time(period=period_2, timestamp=timedelta(seconds=45 * 60)),
        )
        assert home_ending_lam.player_id == "228268"  # Bryce Everett Jamison

        away_starting_gk = dataset.metadata.teams[1].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=92)),
        )
        assert away_starting_gk.player_id == "244046"  # 'Kristopher Shakes'

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        assert dataset.metadata.pitch_dimensions == MetricPitchDimensions(
            x_dim=Dimension(0, 105),
            y_dim=Dimension(0, 68),
            standardized=False,
        )

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        assert dataset.metadata.coordinate_system == build_coordinate_system(
            Provider.SMRTSTATS
        )

    def test_timestamp_of_first_event_of_periods(self, dataset):
        for period in dataset.metadata.periods:
            first_event_of_period = next(
                e for e in dataset.events if e.period.id == period.id
            )
            assert first_event_of_period.timestamp <= timedelta(seconds=3)


class TestSmrtStatsEvent:
    """Generic tests related to deserializing events"""

    def test_generic_attributes(self, dataset: EventDataset):
        """Test generic event attributes"""
        event = dataset.get_event_by_id("239947304")
        assert event.event_id == "239947304"
        assert event.team.name == "Orange County SC"
        assert event.ball_owning_team.name == "Orange County SC"
        assert event.player.name == "Cameron Gatlin Dunbar"
        assert event.coordinates == Point(x=52.5, y=34.0)
        assert event.raw_event["id"] == 239947304
        assert event.period.id == 1
        assert event.timestamp == timedelta(seconds=0)
        # assert event.ball_state == BallState.ALIVE


class TestSmrtStatsPassEvent:
    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all pass events"""
        events = dataset.find_all("pass")
        assert len(events) == 829

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play pass"""
        pass_event = dataset.get_event_by_id("239947306")
        # A pass should have a result
        assert pass_event.result == PassResult.COMPLETE
        # A pass should have end coordinates
        assert pass_event.receiver_coordinates == Point(x=87.15, y=55.76)
        # A pass should have a receiver
        assert (
            pass_event.receiver_player.name == "Lyam Khonick MacKinnon Diouf"
        )

        # A pass can have set piece qualifiers
        assert pass_event.get_qualifier_value(SetPieceQualifier) is None
        # A pass can have pass qualifiers
        assert pass_event.get_qualifier_value(PassQualifier) is None

    def test_pass_qualifiers(self, dataset: EventDataset):
        """It should add pass qualifiers"""
        pass_event = dataset.get_event_by_id("239947531")
        assert pass_event.get_qualifier_values(PassQualifier) == [
            PassType.CROSS
        ]
        assert pass_event.get_qualifier_values(SetPieceQualifier) == [
            SetPieceType.CORNER_KICK
        ]

    def test_set_piece(self, dataset: EventDataset):
        """It should add set piece qualifiers to free kick passes"""
        pass_event = dataset.get_event_by_id("239947311")
        assert (
            pass_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.FREE_KICK
        )

    def test_interception(self, dataset: EventDataset):
        """It should split interception passes into two events"""
        interception = dataset.get_event_by_id("239947350")
        assert interception.event_type == EventType.INTERCEPTION
        assert interception.result == InterceptionResult.SUCCESS

    def test_aerial_duel(self, dataset: EventDataset):
        """It should split passes that follow an aerial duel into two events"""
        duel = dataset.get_event_by_id("239947354")
        assert duel.event_type == EventType.DUEL
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.AERIAL,
        ]
        assert duel.result == DuelResult.WON


class TestSmrtStatsShotEvent:
    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("shot")
        assert len(events) == 25

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play shot"""
        shot = dataset.get_event_by_id("239947536")
        # A shot event should have a result
        assert shot.result == ShotResult.OFF_TARGET
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(x=105, y=15.27, z=1.97)

    # def test_free_kick(self, dataset: EventDataset):
    #     """It should add set piece qualifiers to free kick shots"""
    #     shot = dataset.get_event_by_id("7c10ac89-738c-4e99-8c0c-f55bc5c0995e")
    #     assert (
    #         shot.get_qualifier_value(SetPieceQualifier)
    #         == SetPieceType.FREE_KICK
    #     )


class TestSmrtStatsInterceptionEvent:
    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all interception events"""
        events = dataset.find_all("interception")
        assert len(events) == 20

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of interceptions"""
        interception = dataset.get_event_by_id("239947356")
        assert interception.result == InterceptionResult.SUCCESS


class TestSmrtStatsClearanceEvent:
    """Tests related to deserializing 9/Clearance events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 39  # clearances + keeper sweeper

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of clearances"""
        clearance = dataset.get_event_by_id("239947418")
        # A clearance has no result
        assert clearance.result is None


# class TestSmrtStatsMiscontrolEvent:
#     """Tests related to deserializing 19/Miscontrol events"""
#
#     def test_deserialize_all(self, dataset: EventDataset):
#         """It should deserialize all miscontrol events"""
#         events = dataset.find_all("miscontrol")
#         assert len(events) == 22
#
#     def test_attributes(self, dataset: EventDataset):
#         """Verify specific attributes of miscontrols"""
#         miscontrol = dataset.get_event_by_id(
#             "e297def3-9907-414a-9eb5-e1269343b84d"
#         )
#         # A miscontrol has no result
#         assert miscontrol.result is None
#         # A miscontrol has no qualifiers
#         assert miscontrol.qualifiers is None
#
#     def test_aerial_duel(self, dataset: EventDataset):
#         """It should split clearances that follow an aerial duel into two events"""
#         assert True  # can happen according to the documentation, but not in the dataset


class TestSmrtStatsDribbleEvent:
    """Tests related to deserializing 17/Dribble events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all dribble events"""
        events = dataset.find_all("take_on")
        assert len(events) == 23

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of dribbles"""
        dribble = dataset.get_event_by_id("239947361")
        # A dribble should have a result
        assert dribble.result == TakeOnResult.COMPLETE

    def test_result_out(self, dataset: EventDataset):
        """The result of a dribble can be TakeOnResult.INCOMPLETE"""
        dribble = dataset.get_event_by_id("239947409")
        assert dribble.result == TakeOnResult.INCOMPLETE


# class TestSmrtStatsCarryEvent:
#     """Tests related to deserializing 22/Carry events"""
#
#     def test_deserialize_all(self, dataset: EventDataset):
#         """It should deserialize all carry events"""
#         events = dataset.find_all("carry")
#         assert len(events) == 929
#
#     def test_attributes(self, dataset: EventDataset):
#         """Verify specific attributes of carries"""
#         carry = dataset.get_event_by_id("fab6360a-cbc2-45a3-aafa-5f3ec81eb9c7")
#         # A carry is always successful
#         assert carry.result == CarryResult.COMPLETE
#         # A carry should have an end location
#         assert carry.end_coordinates == Point(21.65, 54.85)
#         # A carry should have an end timestamp
#         assert carry.end_timestamp == parse_str_ts("00:20:11.457") + timedelta(
#             seconds=1.365676
#         )


class TestSmrtStatsDuelEvent:
    """Tests related to deserializing 1/Duel events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all duel and 50/50 events"""
        events = dataset.find_all("duel")
        assert len(events) == 144

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of duels"""
        duel = dataset.get_event_by_id("239947411")
        # A duel should have a result
        assert duel.result == DuelResult.WON
        # A duel should have a duel type
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.GROUND,
            DuelType.TACKLE,
        ]

    def test_aerial_duel_qualifiers(self, dataset: EventDataset):
        """It should add aerial duel + loose ball qualifiers"""
        duel = dataset.get_event_by_id("239947312")
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.AERIAL,
        ]


class TestSmrtStatsGoalkeeperEvent:
    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all goalkeeper events"""
        events = dataset.find_all("goalkeeper")
        assert len(events) == 15

    def test_save(self, dataset: EventDataset):
        """It should deserialaize goalkeeper saves"""
        # A save should be deserialized as a goalkeeper event
        save = dataset.get_event_by_id("239947546")
        assert save.get_qualifier_value(GoalkeeperQualifier) == (
            GoalkeeperActionType.SAVE
        )


class TestSmrtStatsSubstitutionEvent:
    """Tests related to deserializing 18/Substitution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all substitution events"""
        events = dataset.find_all("substitution")
        assert len(events) == 10

        first_sub_event = events[0]
        assert first_sub_event.player == dataset.metadata.teams[
            0
        ].get_player_by_id("182350")
        assert first_sub_event.replacement_player == dataset.metadata.teams[
            0
        ].get_player_by_id("356")


class TestsSmrtStatsBadBehaviourEvent:
    """Tests related to deserializing 22/Bad Behaviour events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should create a card event for each card given"""
        events = dataset.find_all("card")
        assert len(events) == 9

        for event in events:
            assert event.card_type == CardType.FIRST_YELLOW


class TestSmrtStatsFoulCommittedEvent:
    """Tests related to deserializing 2/Foul Committed events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all foul committed events"""
        events = dataset.find_all("foul_committed")
        assert len(events) == 33


# class TestSmrtStatsRecoveryEvent:
#     """Tests related to deserializing 23/Recovery events"""
#
#     def test_deserialize_successful(self, dataset: EventDataset):
#         """It should deserialize all successful ball recovery events"""
#         events = dataset.find_all("recovery")
#         assert len(events) == 93
#
#     def test_deserialize_failed(self, dataset: EventDataset):
#         """It should deserialize all failed ball recovery events as loose ball duels"""
#         failed_recovery = dataset.get_event_by_id(
#             "0df4c1d6-1c4a-407b-876d-d9ac80fd7eee"
#         )
#         assert failed_recovery.event_type == EventType.DUEL
#         assert failed_recovery.get_qualifier_values(DuelQualifier) == [
#             DuelType.LOOSE_BALL,
#         ]
#         assert failed_recovery.result == DuelResult.LOST


# class TestSmrtStatsTacticalShiftEvent:
#     """Tests related to deserializing 34/Tactical Shift events"""
#
#     def test_deserialize_all(self, dataset: EventDataset):
#         """It should deserialize all tactical shift events"""
#         events = dataset.find_all("formation_change")
#         assert len(events) == 2
#
#     def test_attributes(self, dataset: EventDataset):
#         """Verify specific attributes of tactical shift events"""
#         formation_change = dataset.get_event_by_id(
#             "983cdd00-6f7f-4d62-bfc2-74e4e5b0137f"
#         )
#         assert formation_change.formation_type == FormationType("4-3-3")
#
#     def test_player_position(self, base_dir):
#         dataset = smrtstats.load(
#             lineup_data=base_dir / "files/smrtstats_lineup.json",
#             event_data=base_dir / "files/smrtstats_event.json",
#         )
#
#         for item in dataset.aggregate("minutes_played", include_position=True):
#             print(
#                 f"{item.player} {item.player.player_id}- {item.start_time} - {item.end_time} - {item.duration} - {item.position}"
#             )
#
#         home_team, away_team = dataset.metadata.teams
#         period1, period2 = dataset.metadata.periods
#
#         player = home_team.get_player_by_id(6379)
#         assert player.positions.ranges() == [
#             (
#                 period1.start_time,
#                 period2.start_time,
#                 PositionType.RightMidfield,
#             ),
#             (
#                 period2.start_time,
#                 period2.end_time,
#                 PositionType.RightBack,
#             ),
#         ]
#
#         # This player gets a new position 30 sec after he gets on the pitch, these two positions must be merged
#         player = away_team.get_player_by_id(6935)
#         assert player.positions.ranges() == [
#             (
#                 period2.start_time + timedelta(seconds=1362.254),
#                 period2.end_time,
#                 PositionType.LeftMidfield,
#             )
#         ]
