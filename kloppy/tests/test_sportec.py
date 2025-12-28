from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from kloppy import sportec
from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    DatasetFlag,
    DatasetType,
    Dimension,
    DuelQualifier,
    DuelResult,
    DuelType,
    EventDataset,
    FormationType,
    MetricPitchDimensions,
    Official,
    OfficialType,
    Orientation,
    Origin,
    PassQualifier,
    PassResult,
    PassType,
    Point,
    Point3D,
    PositionType,
    Provider,
    Score,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    SportecEventDataCoordinateSystem,
    SubstitutionEvent,
    TakeOnResult,
    Time,
    TrackingDataset,
    VerticalOrientation,
)
from kloppy.domain.models.event import EventType


@pytest.fixture(scope="module")
def event_data(base_dir) -> str:
    return base_dir / "files" / "sportec_events_J03WPY.xml"


@pytest.fixture(scope="module")
def meta_data(base_dir) -> str:
    return base_dir / "files" / "sportec_meta_J03WPY.xml"


@pytest.fixture(scope="module")
def dataset(event_data: Path, meta_data: Path):
    return sportec.load_event(
        event_data=event_data, meta_data=meta_data, coordinates="sportec"
    )


class TestSportecMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the Sportec provider"""
        assert dataset.metadata.provider == Provider.SPORTEC

    def test_date(self, dataset):
        """It should set the correct match date"""
        assert dataset.metadata.date == datetime.fromisoformat(
            "2022-10-15T11:01:28.300+00:00"
        )

    def test_game_id(self, dataset):
        """It should set the correct game id"""
        assert dataset.metadata.game_id == "DFL-MAT-J03WPY"

    def test_game_week(self, dataset):
        """It should set the correct game week"""
        assert dataset.metadata.game_week == 12

    def test_orientation(self, dataset):
        """It should set the action-executing-team orientation"""
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_frame_rate(self, dataset):
        """It should set the frame rate to None"""
        assert dataset.metadata.frame_rate is None

    def test_teams(self, dataset):
        """It should create the teams and player objects"""
        # There should be two teams with the correct names and starting formations
        assert dataset.metadata.teams[0].name == "Fortuna Düsseldorf"
        assert dataset.metadata.teams[0].coach == "Daniel Thioune"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-2-3-1"
        )
        assert dataset.metadata.teams[1].name == "1. FC Nürnberg"
        assert dataset.metadata.teams[1].coach == "M. Weinzierl"
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-1-3-2"
        )
        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("DFL-OBJ-0000NZ")
        assert player.player_id == "DFL-OBJ-0000NZ"
        assert player.jersey_no == 25
        assert player.full_name == "Matthias Zimmermann"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        # Starting players get their position from the STARTING_XI event
        player = dataset.metadata.teams[0].get_player_by_id("DFL-OBJ-0000NZ")

        assert player.starting_position == PositionType.RightBack
        assert player.starting

        # Substituted players have a position
        sub_player = dataset.metadata.teams[0].get_player_by_id(
            "DFL-OBJ-00008K"
        )
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
        assert home_starting_gk.player_id == "DFL-OBJ-0028FW"  # Kastenmeier

        home_starting_cam = dataset.metadata.teams[0].get_player_by_position(
            PositionType.CenterAttackingMidfield,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_cam.player_id == "DFL-OBJ-002G5J"  # Appelkamp

        home_ending_cam = dataset.metadata.teams[0].get_player_by_position(
            PositionType.CenterAttackingMidfield,
            time=Time(period=period_2, timestamp=timedelta(seconds=45 * 60)),
        )
        assert home_ending_cam.player_id == "DFL-OBJ-00008K"  # Hennings

        away_starting_gk = dataset.metadata.teams[1].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=92)),
        )
        assert away_starting_gk.player_id == "DFL-OBJ-0001HW"  # Mathenia

    def test_periods(self, dataset):
        """It should create the periods"""
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[
            0
        ].start_timestamp == datetime.fromisoformat(
            "2022-10-15T13:01:28.310+02:00"
        )
        assert dataset.metadata.periods[
            0
        ].end_timestamp == datetime.fromisoformat(
            "2022-10-15T13:47:31.000+02:00"
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[
            1
        ].start_timestamp == datetime.fromisoformat(
            "2022-10-15T14:03:29.010+02:00"
        )
        assert dataset.metadata.periods[
            1
        ].end_timestamp == datetime.fromisoformat(
            "2022-10-15T14:54:41.000+02:00"
        )

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        assert dataset.metadata.pitch_dimensions == MetricPitchDimensions(
            x_dim=Dimension(0, 105),
            y_dim=Dimension(0, 68),
            standardized=False,
            pitch_length=105,
            pitch_width=68,
        )

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        coordinate_system = dataset.metadata.coordinate_system
        assert isinstance(coordinate_system, SportecEventDataCoordinateSystem)
        assert coordinate_system.origin == Origin.BOTTOM_LEFT
        assert (
            coordinate_system.vertical_orientation
            == VerticalOrientation.BOTTOM_TO_TOP
        )
        assert coordinate_system.normalized is False

    def test_score(self, dataset):
        """It should set the correct score"""
        assert dataset.metadata.score == Score(0, 1)

    def test_officials(self, dataset):
        """It should set the correct officials"""
        referees = {role: list() for role in OfficialType}
        for referee in dataset.metadata.officials:
            referees[referee.role].append(referee)
        # main referee
        assert referees[OfficialType.MainReferee][0].name == "W. Haslberger"
        assert referees[OfficialType.MainReferee][0].first_name == "Wolfgang"
        assert referees[OfficialType.MainReferee][0].last_name == "Haslberger"
        # assistants
        assert referees[OfficialType.AssistantReferee][0].name == "D. Riehl"
        assert referees[OfficialType.AssistantReferee][1].name == "L. Erbst"
        assert referees[OfficialType.FourthOfficial][0].name == "N. Fuchs"
        assert (
            referees[OfficialType.VideoAssistantReferee][0].name
            == "D. Schlager"
        )

    def test_flags(self, dataset):
        """It should set the correct flags"""
        assert dataset.metadata.flags == DatasetFlag.BALL_STATE


class TestSportecEventData:
    """Generic tests related to deserializing events"""

    def test_generic_attributes(self, dataset: EventDataset):
        """Test generic event attributes"""
        event = dataset.get_event_by_id("18237400000011")
        assert event.event_id == "18237400000011"
        assert event.team.name == "1. FC Nürnberg"
        assert event.ball_owning_team is None
        assert event.player.name == "James Lawrence"
        assert event.coordinates == Point(11.72, 50.25)
        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)
        assert event.raw_event["EventId"] == "18237400000011"
        assert event.related_event_ids == []
        assert event.period.id == 1
        assert event.timestamp == (
            datetime.fromisoformat(
                "2022-10-15T13:01:43.407+02:00"
            )  # event timestamp
            - datetime.fromisoformat(
                "2022-10-15T13:01:28.310+02:00"
            )  # period start
        )
        assert event.ball_state == BallState.ALIVE

    def test_timestamp(self, dataset: EventDataset):
        """It should set the correct timestamp, reset to zero after each period"""
        kickoff_p1 = dataset.get_event_by_id("18237400000006")
        assert kickoff_p1.timestamp == timedelta(seconds=0)
        kickoff_p2 = dataset.get_event_by_id("18237400000772")
        assert kickoff_p2.timestamp == timedelta(seconds=0)

    def test_ball_out_of_play(self, dataset: EventDataset):
        """It should add a synthetic ball out event before each throw-in/corner/goal kick"""
        ball_out_events = dataset.find_all("ball_out")
        assert len(ball_out_events) == (
            41  # throw-ins
            + 11  # corners
            + 18  # goal kicks
        )

        ball_out_event = dataset.get_event_by_id("18237400000023-out")
        # Timestamp is set from "DecisionTimestamp"
        assert ball_out_event.timestamp == (
            datetime.fromisoformat(
                "2022-10-15T13:02:10.879+02:00"
            )  # event timestamp
            - datetime.fromisoformat(
                "2022-10-15T13:01:28.310+02:00"
            )  # period start
        )

    def test_correct_normalized_deserialization(
        self, event_data: Path, meta_data: Path
    ):
        """Test if the normalized deserialization is correct"""
        dataset = sportec.load_event(
            event_data=event_data, meta_data=meta_data, coordinates="kloppy"
        )

        # The events should have standardized coordinates
        kickoff = dataset.get_event_by_id("18237400000006")
        assert kickoff.coordinates.x == pytest.approx(0.5, abs=1e-2)
        assert kickoff.coordinates.y == pytest.approx(0.5, abs=1e-2)

    def test_supported_events(self, dataset: EventDataset):
        """It should parse all supported event types"""
        # Test the kloppy event types that are being parsed
        event_types_set = set(event.event_type for event in dataset.events)

        assert EventType.GENERIC in event_types_set
        assert EventType.SHOT in event_types_set
        assert EventType.PASS in event_types_set
        assert EventType.RECOVERY in event_types_set
        assert EventType.SUBSTITUTION in event_types_set
        assert EventType.CARD in event_types_set
        assert EventType.FOUL_COMMITTED in event_types_set
        assert EventType.CLEARANCE in event_types_set
        assert EventType.INTERCEPTION in event_types_set
        assert EventType.DUEL in event_types_set
        assert EventType.TAKE_ON in event_types_set

    def test_unsupported_events(self, dataset: EventDataset):
        generic_events = dataset.find_all("generic")
        generic_event_types = {e.event_name for e in generic_events}
        for event in generic_events:
            if event.event_name == "generic":
                print(event.raw_event)
        assert generic_event_types == {
            "OtherBallAction",  # Are these carries and clearances?
            "TacklingGame:Layoff",  # What are layoffs?
            "FairPlay",
            "PossessionLossBeforeGoal",
            "BallClaiming:BallHeld",  # Probably a goalkeeper event
            "Nutmeg",
            "PenaltyNotAwarded",
            "Run",
            "SpectacularPlay",  # Should be mapped to a pass?
            "Offside",  # Add as qualifier
            "BallDeflection",
            "RefereeBall",
            "FinalWhistle",
        }


class TestSportecShotEvent:
    """Tests related to deserializing Shot events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("shot")
        assert len(events) == 26  # <ShotAtGoal> events

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play shot"""
        shot = dataset.get_event_by_id("18237400000125")
        # A shot event should have a result
        assert shot.result == ShotResult.SAVED
        # Not implemented or not supported?
        assert shot.result_coordinates is None
        # A shot event should have a body part
        assert shot.get_qualifier_value(BodyPartQualifier) == BodyPart.LEFT_FOOT
        # An open play shot should not have a set piece qualifier
        assert shot.get_qualifier_value(SetPieceQualifier) is None
        # A shot event should have a xG value
        assert (
            next(
                statistic
                for statistic in shot.statistics
                if statistic.name == "xG"
            ).value
            == 0.5062
        )

    # def test_free_kick(self, dataset: EventDataset):
    #     """It should add set piece qualifiers to free kick shots"""
    #     shot = dataset.get_event_by_id("???")
    #     assert (
    #         shot.get_qualifier_value(SetPieceQualifier)
    #         == SetPieceType.FREE_KICK
    #     )


class TestSportecPlayEvent:
    """Tests related to deserializing Pass and Cross events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all pass events"""
        events = dataset.find_all("pass")
        assert len(events) == 858 + 33  # pass 858 + cross 33

    def test_open_play_pass(self, dataset: EventDataset):
        """Verify specific attributes of simple open play pass"""
        pass_event = dataset.get_event_by_id("18237400000007")
        # A pass should have a result
        assert pass_event.result == PassResult.COMPLETE
        # A pass should have end coordinates
        assert pass_event.receiver_coordinates == Point(35.27, 5.89)
        # Sportec does not provide the end timestamp
        assert pass_event.receive_timestamp is None
        # A pass should have a receiver
        assert pass_event.receiver_player.name == "Dawid Kownacki"
        # Sportec only sets the bodypart for shots
        assert pass_event.get_qualifier_value(BodyPartQualifier) is None
        # A pass can have set piece qualifiers
        assert pass_event.get_qualifier_value(SetPieceQualifier) is None

    def test_pass_result(self, dataset: EventDataset):
        """It should set the correct pass result"""
        # Evaluation="successfullyCompleted"
        completed_pass = dataset.get_event_by_id("18237400000007")
        assert completed_pass.result == PassResult.COMPLETE
        # Evaluation="unsuccessful"
        failed_pass = dataset.get_event_by_id("18237400000013")
        assert failed_pass.result == PassResult.INCOMPLETE
        # Evaluation="unsuccessful" + next event is throw-in
        failed_pass_out = dataset.get_event_by_id("18237400000076")
        assert failed_pass_out.result == PassResult.OUT
        # Evaluation="unsuccessful" + next event is offside
        failed_pass_offside = dataset.get_event_by_id("18237400000693")
        assert failed_pass_offside.result == PassResult.OFFSIDE

    def test_receiver_coordinates(self, dataset: EventDataset):
        """Completed pass should have receiver coordinates"""
        pass_events = dataset.find_all("pass.complete")
        for pass_event in pass_events:
            if "Recipient" in pass_event.raw_event:
                if pass_event.receiver_coordinates is None:
                    print(pass_event.event_id)
                assert pass_event.receiver_coordinates is not None

    def test_pass_qualifiers(self, dataset: EventDataset):
        """It should add pass qualifiers"""
        pass_event = dataset.get_event_by_id("18237400000007")
        assert set(pass_event.get_qualifier_values(PassQualifier)) == {
            PassType.SWITCH_OF_PLAY,
            PassType.HIGH_PASS,
            PassType.LONG_BALL,
        }

    def test_set_piece(self, dataset: EventDataset):
        """It should add set piece qualifiers to free kick passes"""
        pass_event = dataset.get_event_by_id("18237400000006")
        assert (
            pass_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )


class TestSportecBallClaimingEvent:
    """Tests related to deserializing BallClaiming events"""

    def test_deserialize_ball_claimed(self, dataset: EventDataset):
        """It should deserialize all Type='BallClaimed' events as recoveries"""
        events = dataset.find_all("recovery")
        assert len(events) == 7

    def test_deserialize_intercepted_ball(self, dataset: EventDataset):
        """It should deserialize all Type='InterceptedBall' events as interceptions"""
        events = dataset.find_all("interception")
        assert len(events) == 4

        interception = dataset.get_event_by_id("18237403501368")
        assert interception.result is None  # TODO: infer result
        assert interception.get_qualifier_value(BodyPartQualifier) is None


class TestSportecCautionEvent:
    """Tests related to deserializing Caution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should create a card event for each Caution event."""
        events = dataset.find_all("card")
        assert len(events) == 9

        for event in events:
            assert event.card_type == CardType.FIRST_YELLOW

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of cards"""
        card = dataset.get_event_by_id("18237400001225")
        # A card should have a card type
        assert card.card_type == CardType.FIRST_YELLOW
        # Card qualifiers should not be added
        assert card.get_qualifier_value(CardQualifier) is None


class TestSportecFoulEvent:
    """Tests related to deserializing Foul events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all foul events"""
        events = dataset.find_all("foul_committed")
        assert len(events) == 18

    def test_player(self, dataset: EventDataset):
        """It should get the player who committed the foul"""
        foul = dataset.get_event_by_id("18237400000878")
        assert foul.player.player_id == "DFL-OBJ-002G68"
        assert foul.team.team_id == "DFL-CLU-000005"

    def test_ball_state(self, dataset: EventDataset):
        """It should set the ball state to dead for fouls"""
        foul = dataset.get_event_by_id("18237400000894")
        assert foul.ball_state == BallState.DEAD

    def test_card(self, dataset: EventDataset):
        """It should add a card qualifier if a card was given"""
        foul_with_card = dataset.get_event_by_id("18237400000894")
        assert (
            foul_with_card.get_qualifier_value(CardQualifier)
            == CardType.FIRST_YELLOW
        )

        foul_without_card = dataset.get_event_by_id("18237400001114")
        assert foul_without_card.get_qualifier_value(CardQualifier) is None


class TestSportecDefensiveClearanceEvent:
    """Tests related to deserializing OtherBallAction>DefensiveClearance events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 15

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of clearances"""
        clearance = dataset.get_event_by_id("18237400000679")
        # A clearance has no result
        assert clearance.result is None
        # A clearance has no bodypart
        assert clearance.get_qualifier_value(BodyPartQualifier) is None


class TestSportecSubstitutionEvent:
    """Tests related to deserializing Substitution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all substitution events"""
        events = dataset.find_all("substitution")
        assert len(events) == 9

        # Verify that the player and replacement player are set correctly
        subs = [
            ("DFL-OBJ-002G5J", "DFL-OBJ-00008K"),
            ("DFL-OBJ-0026RH", "DFL-OBJ-J01CP5"),
            ("DFL-OBJ-J01H9X", "DFL-OBJ-J01NQ8"),
            ("DFL-OBJ-002595", "DFL-OBJ-0026IA"),
            ("DFL-OBJ-J0178P", "DFL-OBJ-002G78"),
            ("DFL-OBJ-002FYC", "DFL-OBJ-00286U"),
            ("DFL-OBJ-0000F8", "DFL-OBJ-002GM1"),
            ("DFL-OBJ-0000EJ", "DFL-OBJ-J01K2L"),
            ("DFL-OBJ-0001LJ", "DFL-OBJ-0001BX"),
        ]
        for event_idx, (player_id, replacement_player_id) in enumerate(subs):
            event = cast(SubstitutionEvent, events[event_idx])
            assert event.player == event.team.get_player_by_id(player_id)
            assert event.replacement_player == event.team.get_player_by_id(
                replacement_player_id
            )


class TestSportecTacklingGameEvent:
    def test_deserialize_takeon(self, dataset: EventDataset):
        """It should deserialize all TacklingGame events with a DribbleEvaluation attribute as take-ons."""
        events = dataset.find_all("take_on")
        assert len(events) == 17

        # A dribble should have a result and a duel associated with it
        completed_dribble = dataset.get_event_by_id("18237400000845-Winner")
        assert completed_dribble.result == TakeOnResult.COMPLETE
        lost_duel = dataset.get_event_by_id("18237400000845-Loser")
        assert lost_duel.event_type == EventType.DUEL
        assert lost_duel.get_qualifier_value(DuelQualifier) == DuelType.GROUND

        failed_dribble = dataset.get_event_by_id("18237400001220-Loser")
        assert failed_dribble.result == TakeOnResult.INCOMPLETE
        won_duel = dataset.get_event_by_id("18237400001220-Winner")
        assert won_duel.event_type == EventType.DUEL
        assert won_duel.get_qualifier_value(DuelQualifier) == DuelType.GROUND

        # A dribble can have as result OUT
        # dribble = dataset.get_event_by_id("???")
        # assert dribble.result == TakeOnResult.OUT

    def test_deserialize_duel(self, dataset: EventDataset):
        # ("WinnerResult", "ballClaimed")  --> player with ball control looses duel
        duel_won = dataset.get_event_by_id("18237400000092-Winner")
        duel_won.player.player_id == "DFL-OBJ-0000EJ"
        assert duel_won.event_type == EventType.DUEL
        assert duel_won.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_won.result == DuelResult.WON
        duel_lost = dataset.get_event_by_id("18237400000092-Loser")
        duel_lost.player.player_id == "DFL-OBJ-002FXT"
        assert duel_lost.event_type == EventType.DUEL
        assert duel_lost.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_lost.result == DuelResult.LOST
        # ("WinnerResult", "ballControlRetained") --> player with ball control wins duel
        duel_won = dataset.get_event_by_id("18237400000870-Winner")
        duel_won.player.player_id == "DFL-OBJ-002FYC"
        assert duel_won.event_type == EventType.DUEL
        assert duel_won.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_won.result == DuelResult.WON
        duel_lost = dataset.get_event_by_id("18237400000870-Loser")
        duel_lost.player.player_id == "DFL-OBJ-0000F8"
        assert duel_lost.event_type == EventType.DUEL
        assert duel_lost.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_lost.result == DuelResult.LOST
        # ("WinnerResult", "ballcontactSucceeded")  --> defender can touch the ball without recovering
        duel_won = dataset.get_event_by_id("18237400000874-Winner")
        duel_won.player.player_id == "DFL-OBJ-002FYC"
        assert duel_won.event_type == EventType.DUEL
        assert duel_won.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_won.result == DuelResult.NEUTRAL
        duel_lost = dataset.get_event_by_id("18237400000874-Loser")
        duel_lost.player.player_id == "DFL-OBJ-002GMO"
        assert duel_lost.event_type == EventType.DUEL
        assert duel_lost.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_lost.result == DuelResult.NEUTRAL
        # ("WinnerResult", "layoff")
        # TODO: not sure what this is
        duel_won = dataset.get_event_by_id("18237400000945-Winner")
        duel_won.player.player_id == "DFL-OBJ-0026RH"
        assert duel_won.event_type == EventType.GENERIC
        duel_lost = dataset.get_event_by_id("18237400000945-Loser")
        duel_lost.player.player_id == "DFL-OBJ-0028T3"
        assert duel_lost.event_type == EventType.GENERIC
        # ("WinnerResult", "fouled")
        duel_won = dataset.get_event_by_id("18237400000877-Winner")
        duel_won.player.player_id == "DFL-OBJ-002FXT"
        assert duel_won.event_type == EventType.DUEL
        assert duel_won.get_qualifier_value(DuelQualifier) == DuelType.GROUND
        assert duel_won.result == DuelResult.WON
        duel_lost = dataset.get_event_by_id("18237400000877-Loser")
        assert duel_lost is None
        foul = dataset.get_event_by_id("18237400000878")
        foul.player.player_id == "DFL-OBJ-002G68"
        assert foul.event_type == EventType.FOUL_COMMITTED

    def test_deserialize_air_duel(self, dataset: EventDataset):
        duel_won = dataset.get_event_by_id("18237400000925-Winner")
        duel_won.player.player_id == "DFL-OBJ-0000EJ"
        assert duel_won.event_type == EventType.DUEL
        assert duel_won.get_qualifier_value(DuelQualifier) == DuelType.AERIAL
        assert duel_won.result == DuelResult.NEUTRAL
        duel_lost = dataset.get_event_by_id("18237400000925-Loser")
        duel_lost.player.player_id == "DFL-OBJ-002FXT"
        assert duel_lost.event_type == EventType.DUEL
        assert duel_lost.get_qualifier_value(DuelQualifier) == DuelType.AERIAL
        assert duel_lost.result == DuelResult.NEUTRAL


class TestSportecDeleteEvent:
    def test_deserialize_delete_event(self, dataset: EventDataset):
        """Delete events are thrown away"""
        delete_event = dataset.get_event_by_id("18237400000016")
        assert delete_event is None


class TestSportecLegacyEventData:
    """Tests on some old private Sportec event data."""

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/sportec_events.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta.xml"

    @pytest.fixture
    def dataset(self, event_data: Path, meta_data: Path):
        return sportec.load_event(
            event_data=event_data, meta_data=meta_data, coordinates="sportec"
        )

    def test_correct_event_data_deserialization(self, dataset: EventDataset):
        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        assert len(dataset.events) == 33
        assert dataset.events[31].result == ShotResult.OWN_GOAL

        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == datetime(
            2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[0].end_timestamp == datetime(
            2020, 6, 5, 19, 16, 24, 0, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == datetime(
            2020, 6, 5, 19, 33, 27, 10000, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[1].end_timestamp == datetime(
            2020, 6, 5, 20, 23, 18, 0, tzinfo=timezone.utc
        )

        # Check the timestamps
        assert dataset.events[0].timestamp == timedelta(seconds=0)
        assert dataset.events[1].timestamp == timedelta(seconds=3.123)
        assert dataset.events[28].timestamp == timedelta(seconds=0)

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "DFL-OBJ-00001D"
        assert player.jersey_no == 1
        assert str(player) == "A. Schwolow"
        assert player.starting_position == PositionType.Goalkeeper

        # Check the qualifiers
        assert (
            dataset.events[28].get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )
        assert (
            dataset.events[18].get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )
        assert (
            dataset.events[26].get_qualifier_value(BodyPartQualifier)
            == BodyPart.LEFT_FOOT
        )
        assert (
            dataset.events[29].get_qualifier_value(BodyPartQualifier)
            == BodyPart.HEAD
        )

        assert dataset.events[0].coordinates == Point(56.41, 68.0)

    def test_correct_normalized_event_data_deserialization(
        self, event_data: Path, meta_data: Path
    ):
        dataset = sportec.load_event(event_data=event_data, meta_data=meta_data)

        assert dataset.events[0].coordinates == Point(0.5641, 0.0)

    def test_pass_receiver_coordinates(self, dataset: EventDataset):
        """Pass receiver_coordinates must match the X/Y-Source-Position of next event"""
        first_pass = dataset.find("pass")
        assert first_pass.receiver_coordinates != first_pass.next().coordinates
        assert first_pass.receiver_coordinates == Point(x=77.75, y=38.71)


class TestSportecTrackingData:
    """
    Tests for loading Sportec tracking data.
    """

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def raw_data_referee(self, base_dir) -> str:
        return base_dir / "files/sportec_positional_w_referee.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta.xml"

    @pytest.fixture
    def dataset(self, raw_data: Path, meta_data: Path) -> TrackingDataset:
        return sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            limit=None,
            only_alive=False,
        )

    def test_load_metadata(self, dataset: TrackingDataset):
        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=400
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=400 + 2786.2
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=4000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=4000 + 2996.68
        )
        assert len(dataset.metadata.officials) == 4

    def test_enriched_metadata(self, dataset: TrackingDataset):
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(
                2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
            )

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "30"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "DFL-MAT-003BN1"

        home_coach = dataset.metadata.teams[0].coach
        if home_coach:
            assert isinstance(home_coach, str)
            assert home_coach == "C. Streich"

        away_coach = dataset.metadata.teams[1].coach
        if away_coach:
            assert isinstance(away_coach, str)
            assert away_coach == "M. Rose"

    def test_load_frames(self, dataset: TrackingDataset):
        home_team, away_team = dataset.metadata.teams

        # It load all frames
        assert len(dataset) == 202

        # Check frame ids
        frame_p1_kick_off = dataset.get_record_by_id(10000)
        assert frame_p1_kick_off is not None
        frame_p2_kick_off = dataset.get_record_by_id(100000)
        assert frame_p2_kick_off is not None

        # Timestamp should be 0.0 for both kick-offs
        assert frame_p1_kick_off.timestamp == timedelta(seconds=0)
        assert frame_p2_kick_off.timestamp == timedelta(seconds=0)

        # Check ball properties
        assert frame_p1_kick_off.ball_state == BallState.DEAD
        assert frame_p1_kick_off.ball_owning_team == away_team
        assert frame_p1_kick_off.ball_coordinates == Point3D(
            x=2.69, y=0.26, z=0.06
        )
        assert dataset.frames[1].ball_speed == 65.59
        assert dataset.frames[1].ball_owning_team == home_team
        assert dataset.frames[1].ball_state == BallState.ALIVE

        # Check player coordinates
        player_lilian = away_team.get_player_by_id("DFL-OBJ-002G3I")
        player_data_p1_kick_off = frame_p1_kick_off.players_data[player_lilian]
        assert player_data_p1_kick_off.coordinates == Point(x=0.35, y=-25.26)
        player_data_p2_kick_off = frame_p2_kick_off.players_data[player_lilian]
        assert player_data_p2_kick_off.coordinates == Point(x=-3.91, y=14.1)

        # We don't load distance right now as it doesn't
        # work together with `sample_rate`: "The distance covered from the previous frame in cm"
        assert player_data_p1_kick_off.distance is None

        # Appears first in 27th frame
        player_bensebaini = away_team.get_player_by_id("DFL-OBJ-002G5S")
        assert player_bensebaini not in dataset.frames[0].players_data
        assert player_bensebaini in dataset.frames[26].players_data

        # Contains all 3 players
        assert len(dataset.frames[35].players_data) == 3

    def test_load_only_alive_frames(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )
        assert len(dataset) == 199
        assert len(dataset.records[2].players_data.keys()) == 1

    def test_limit_sample(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
            limit=100,
        )
        assert len(dataset.records) == 100

        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
            limit=100,
            sample_rate=(1 / 2),
        )
        assert len(dataset.records) == 100

    def test_referees(self, raw_data_referee: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data_referee,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )
        assert len(dataset.metadata.officials) == 4

        assert (
            Official(
                official_id="42",
                name="Pierluigi Collina",
                role=OfficialType.MainReferee,
            ).role.value
            == "Main Referee"
        )

        assert (
            Official(
                official_id="42",
                name="Pierluigi Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Pierluigi Collina"
        )
        assert (
            Official(
                official_id="42",
                first_name="Pierluigi",
                last_name="Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Pierluigi Collina"
        )
        assert (
            Official(
                official_id="42",
                last_name="Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Collina"
        )
        assert (
            Official(official_id="42", role=OfficialType.MainReferee).full_name
            == "main_referee_42"
        )
        assert Official(official_id="42").full_name == "official_42"


# @pytest.mark.parametrize(
#     "match_id",
#     ["J03WPY", "J03WN1", "J03WMX", "J03WOH", "J03WQQ", "J03WOY", "J03WR9"],
# )
# def test_load_open_data(match_id):
#     """Test if it can load all public event data"""
#     dataset = sportec.load_open_event_data(match_id)
#     assert isinstance(dataset, EventDataset)
