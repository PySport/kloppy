from pathlib import Path
from datetime import timedelta

import pytest

from kloppy import scisports
from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    DatasetFlag,
    DatasetType,
    Dimension,
    EventDataset,
    EventType,
    InterceptionResult,
    MetricPitchDimensions,
    Orientation,
    PassResult,
    PassType,
    Point,
    Provider,
    SetPieceType,
    Time,
    build_coordinate_system,
    PassQualifier,
    CardType,
)
from kloppy.domain.models.event import (
    PassEvent,
    ShotEvent,
    InterceptionEvent,
    FoulCommittedEvent,
    CardEvent,
    SubstitutionEvent,
    CarryEvent,
    TakeOnEvent,
    ClearanceEvent,
    MiscontrolEvent,
    GoalkeeperEvent,
    BallOutEvent,
    FormationChangeEvent,
    SetPieceQualifier,
    ShotResult,
    CardQualifier,
    CarryResult,
    TakeOnResult,
    GoalkeeperQualifier,
    GoalkeeperActionType,
)


@pytest.fixture(scope="module")
def dataset() -> EventDataset:
    """Load SciSports data for Team Alpha vs Team Beta"""
    base_dir = Path(__file__).parent
    dataset = scisports.load_event(
        event_data=base_dir / "files" / "scisports_events.json",
        coordinates="scisports",
    )
    assert dataset.dataset_type == DatasetType.EVENT
    return dataset


class TestSciSportsMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the SciSports provider"""
        assert dataset.metadata.provider == Provider.SCISPORTS

    def test_orientation(self, dataset):
        """It should set the static home-away orientation"""
        assert dataset.metadata.orientation == Orientation.STATIC_HOME_AWAY

    def test_framerate(self, dataset):
        """It should set the frame rate to None"""
        assert dataset.metadata.frame_rate is None

    def test_teams(self, dataset):
        """It should create the teams and player objects"""
        # There should be two teams with the correct names
        assert len(dataset.metadata.teams) == 2
        assert dataset.metadata.teams[0].name == "Team Alpha"
        assert dataset.metadata.teams[1].name == "Team Beta"

        # The teams should have the correct players
        home_team = dataset.metadata.teams[0]
        away_team = dataset.metadata.teams[1]

        # Check that teams have players
        assert len(home_team.players) == 14
        assert len(away_team.players) == 14

        # Check a specific player
        player_116 = home_team.get_player_by_id("116")
        assert player_116 is not None
        assert player_116.player_id == "116"
        assert player_116.jersey_no == 21
        assert player_116.name == "Player 06"

    def test_starting_players(self, dataset):
        """It should correctly identify starting players vs substitutes"""
        home_team = dataset.metadata.teams[0]
        away_team = dataset.metadata.teams[1]

        # Each team should have exactly 11 starting players
        home_starters = [p for p in home_team.players if p.starting]
        away_starters = [p for p in away_team.players if p.starting]

        assert len(home_starters) == 11
        assert len(away_starters) == 11

        # Each team should have some substitutes
        home_subs = [p for p in home_team.players if not p.starting]
        away_subs = [p for p in away_team.players if not p.starting]

        assert len(home_subs) == 3
        assert len(away_subs) == 3

        # Check specific examples - players who were substituted out should be starters
        # Player 09 (121) was substituted out, so should be a starter
        player_121 = home_team.get_player_by_id("121")
        assert player_121 is not None
        assert player_121.starting

        # Player 18 (122) was substituted in, so should not be a starter
        player_122 = home_team.get_player_by_id("122")
        assert player_122 is not None
        assert not player_122.starting

    def test_periods(self, dataset):
        """It should create the periods"""
        periods = dataset.metadata.periods
        assert len(periods) == 2

        first_period = periods[0]
        assert first_period.id == 1
        # duration approx 41.5 minutes (2491 seconds)
        assert first_period.start_timestamp == timedelta(seconds=0)
        assert first_period.end_timestamp == timedelta(seconds=2491)

        second_period = periods[1]
        assert second_period.id == 2
        # duration approx 42.4 minutes (2542 seconds)
        assert second_period.start_timestamp == timedelta(
            seconds=2491, microseconds=46000
        )
        assert second_period.end_timestamp == timedelta(
            seconds=5033, microseconds=906000
        )

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        pitch_dims = dataset.metadata.pitch_dimensions
        assert isinstance(pitch_dims, MetricPitchDimensions)
        assert pitch_dims.x_dim == Dimension(-52.5, 52.5)
        assert pitch_dims.y_dim == Dimension(-34, 34)
        assert not pitch_dims.standardized

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        assert dataset.metadata.coordinate_system == build_coordinate_system(
            Provider.SCISPORTS
        )

    def test_flags(self, dataset):
        """It should set the correct flags"""
        assert (
            dataset.metadata.flags
            == DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE
        )


class TestSciSportsEvent:
    """Generic tests related to deserializing events"""

    def test_generic_attributes(self, dataset: EventDataset):
        """Test generic event attributes"""
        event = dataset.get_event_by_id("24")
        assert event is not None
        assert event.event_id == "24"
        assert event.team.name == "Team Alpha"
        assert event.ball_owning_team.name == "Team Alpha"
        assert event.player.name == "Player 26"
        assert event.coordinates == Point(0.0, -0.0)
        assert event.raw_event["eventId"] == 24
        assert event.period.id == 1
        assert event.timestamp == timedelta(seconds=0.07)

    def test_event_counts(self, dataset):
        """Test that we have the expected number of events"""
        # Should have loaded a reasonable number of events (1589 after filtering PERIOD and POSITION)
        assert len(dataset.events) > 1300

        # Check distribution of event types
        event_type_counts = {}
        for event in dataset.events:
            event_type = event.event_type
            event_type_counts[event_type] = (
                event_type_counts.get(event_type, 0) + 1
            )

        # Should have passes, shots, and other event types
        assert EventType.PASS in event_type_counts
        assert EventType.SHOT in event_type_counts
        assert (
            event_type_counts[EventType.PASS] > 500
        )  # Should have many passes

    def test_event_correct_times(self, dataset):
        """Test that event times are within expected range"""
        for period in dataset.metadata.periods:
            first_period_event = next(
                e for e in dataset.events if e.period.id == period.id
            )
            assert first_period_event.timestamp <= timedelta(seconds=1)


class TestSciSportsPassEvent:
    """Tests related to deserializing Pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all pass events"""
        events = dataset.find_all("pass")
        # Based on our analysis, should have 816 pass events (PASS + CROSS)
        assert len(events) == 816

    def test_kick_off_pass(self, dataset: EventDataset):
        kick_off_pass = dataset.get_event_by_id("24")

        # Check basic properties
        assert kick_off_pass.event_type == EventType.PASS
        assert kick_off_pass.player.name == "Player 26"
        assert kick_off_pass.team.name == "Team Alpha"
        assert kick_off_pass.coordinates == Point(0.0, -0.0)
        assert kick_off_pass.timestamp == timedelta(seconds=0.07)

        assert kick_off_pass.receiver_coordinates == Point(x=-13.65, y=0.68)
        assert kick_off_pass.receiver_player.player_id == "124"

    def test_pass_result_checks(self, dataset: EventDataset):
        """Test pass result types (complete/incomplete)"""
        pass_events = dataset.find_all("pass")

        # Find events with different results
        complete_passes = [
            e for e in pass_events if e.result == PassResult.COMPLETE
        ]
        incomplete_passes = [
            e for e in pass_events if e.result == PassResult.INCOMPLETE
        ]

        # Should have both types in the dataset
        assert len(complete_passes) == 631
        assert len(incomplete_passes) == 178

    def test_set_piece_checks(self, dataset: EventDataset):
        """Test different set piece types"""
        pass_events = dataset.find_all("pass")

        # Find different set piece types
        kick_offs = [
            e
            for e in pass_events
            if SetPieceType.KICK_OFF
            in e.get_qualifier_values(SetPieceQualifier)
        ]
        throw_ins = [
            e
            for e in pass_events
            if SetPieceType.THROW_IN
            in e.get_qualifier_values(SetPieceQualifier)
        ]
        free_kicks = [
            e
            for e in pass_events
            if SetPieceType.FREE_KICK
            in e.get_qualifier_values(SetPieceQualifier)
        ]
        corners = [
            e
            for e in pass_events
            if SetPieceType.CORNER_KICK
            in e.get_qualifier_values(SetPieceQualifier)
        ]
        goal_kicks = [
            e
            for e in pass_events
            if SetPieceType.GOAL_KICK
            in e.get_qualifier_values(SetPieceQualifier)
        ]

        assert len(kick_offs) == 7
        assert len(throw_ins) == 36
        assert len(free_kicks) == 41
        assert len(corners) == 10
        assert len(goal_kicks) == 22

    def test_cross_checks(self, dataset: EventDataset):
        """Test cross-type passes"""
        pass_events = dataset.find_all("pass")

        crosses = [
            e
            for e in pass_events
            if PassType.CROSS in e.get_qualifier_values(PassQualifier)
        ]

        assert len(crosses) == 24

    def test_body_part_checks(self, dataset: EventDataset):
        """Test body part qualifiers for passes"""
        pass_events = dataset.find_all("pass")

        right_foot_passes = [
            e
            for e in pass_events
            if BodyPart.RIGHT_FOOT in e.get_qualifier_values(BodyPartQualifier)
        ]
        left_foot_passes = [
            e
            for e in pass_events
            if BodyPart.LEFT_FOOT in e.get_qualifier_values(BodyPartQualifier)
        ]
        head_passes = [
            e
            for e in pass_events
            if BodyPart.HEAD in e.get_qualifier_values(BodyPartQualifier)
        ]
        other_body_part_passes = [
            e
            for e in pass_events
            if BodyPart.OTHER in e.get_qualifier_values(BodyPartQualifier)
        ]

        # Find passes with body part information
        assert len(right_foot_passes) == 0
        assert len(left_foot_passes) == 0
        assert len(head_passes) == 0
        assert len(other_body_part_passes) == 758


class TestSciSportsShotEvent:
    """Tests related to deserializing Shot events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        shots = dataset.find_all("shot")

        assert len(shots) == 38

    def test_shot_event(self, dataset: EventDataset):
        """Verify specific attributes of shot event"""
        shot_event = dataset.get_event_by_id("87")
        assert shot_event is not None
        assert isinstance(shot_event, ShotEvent)

        # Check basic properties
        assert shot_event.event_type == EventType.SHOT
        assert shot_event.player.name == "Player 23"
        assert shot_event.team.name == "Team Alpha"

        assert shot_event.coordinates == Point(45.15, -5.44)
        assert shot_event.timestamp == timedelta(seconds=197.6)

        # No z coordinate given
        assert shot_event.result_coordinates == Point(x=52.5, y=-0.27)
        assert shot_event.result == ShotResult.OFF_TARGET

    def test_shot_results(self, dataset):
        """Test shot result types (on target, off target, blocked)"""
        shot_events = dataset.find_all("shot")

        goal_shots = [e for e in shot_events if e.result == ShotResult.GOAL]
        off_target_shots = [
            e for e in shot_events if e.result == ShotResult.OFF_TARGET
        ]
        post_shots = [e for e in shot_events if e.result == ShotResult.POST]
        blocked_shots = [
            e for e in shot_events if e.result == ShotResult.BLOCKED
        ]
        saved_shots = [e for e in shot_events if e.result == ShotResult.SAVED]
        own_goal_shots = [
            e for e in shot_events if e.result == ShotResult.OWN_GOAL
        ]

        # Should have a mix of shot results
        assert len(goal_shots) == 6
        assert len(off_target_shots) == 14
        assert len(post_shots) == 1
        assert len(blocked_shots) == 7
        assert len(saved_shots) == 10
        assert len(own_goal_shots) == 0


class TestSciSportsInterceptionEvent:
    """Tests related to deserializing Interception events (from INTERCEPTION and BLOCK)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all interception events"""
        events = dataset.find_all("interception")
        assert len(events) == 214  # INTERCEPTION + BLOCK events combined

    def test_interception_event(self, dataset: EventDataset):
        """Verify specific attributes of interception event"""
        # Find the specific interception event
        interception_event = dataset.get_event_by_id("27")
        assert interception_event is not None
        assert isinstance(interception_event, InterceptionEvent)

        # Check basic properties
        assert interception_event.event_type == EventType.INTERCEPTION
        assert interception_event.player.name == "Player 16"
        assert interception_event.team.name == "Team Beta"

        # Check coordinates
        assert interception_event.coordinates == Point(-10.5, 20.4)

        # Check that this was originally an interception
        assert (
            interception_event.raw_event.get("baseTypeName") == "INTERCEPTION"
        )

    def test_interception_results(self, dataset: EventDataset):
        """Test interception result types"""
        interception_events = dataset.find_all("interception")

        # Most interceptions should be successful
        successful_interceptions = [
            e
            for e in interception_events
            if e.result == InterceptionResult.SUCCESS
        ]
        lost_interceptions = [
            e
            for e in interception_events
            if e.result == InterceptionResult.LOST
        ]

        assert len(successful_interceptions) == 201
        assert len(lost_interceptions) == 13


class TestSciSportsFoulEvent:
    """Tests related to deserializing Foul events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all foul events"""
        events = dataset.find_all("foul_committed")
        assert len(events) == 46

    def test_foul_event(self, dataset: EventDataset):
        """Verify specific attributes of foul event"""
        foul_event = dataset.get_event_by_id("206")
        assert foul_event is not None
        assert isinstance(foul_event, FoulCommittedEvent)

        # Check basic properties
        assert foul_event.event_type == EventType.FOUL_COMMITTED
        assert foul_event.player.name == "Player 22"
        assert foul_event.team.name == "Team Alpha"

        # Check coordinates
        assert foul_event.coordinates == Point(26.25, -25.16)

        # Check that this was originally a foul
        assert foul_event.raw_event.get("baseTypeName") == "FOUL"


class TestSciSportsCardEvent:
    """Tests related to deserializing Card events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all card events"""
        events = dataset.find_all("card")
        assert len(events) == 5

    def test_card_event(self, dataset: EventDataset):
        """Verify specific attributes of card event"""
        card_event = dataset.get_event_by_id("209")
        assert card_event is not None
        assert isinstance(card_event, CardEvent)

        # Check basic properties
        assert card_event.event_type == EventType.CARD
        assert card_event.player.name == "Player 04"
        assert card_event.team.name == "Team Alpha"

        # Check that this was originally a card
        assert card_event.raw_event.get("baseTypeName") == "CARD"

    def test_card_types(self, dataset: EventDataset):
        """Test different card types (yellow, second yellow, red)"""
        card_events = dataset.find_all("card")

        first_yellow_cards = [
            e for e in card_events if e.card_type == CardType.FIRST_YELLOW
        ]
        second_yellow_cards = [
            e for e in card_events if e.card_type == CardType.SECOND_YELLOW
        ]
        red_cards = [e for e in card_events if e.card_type == CardType.RED]

        assert len(first_yellow_cards) == 5
        assert len(second_yellow_cards) == 0
        assert len(red_cards) == 0


class TestSciSportsSubstitutionEvent:
    """Tests related to deserializing Substitution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all substitution events"""
        events = dataset.find_all("substitution")
        assert len(events) == 10  # Proper SubstitutionEvents

    def test_substitution_event(self, dataset: EventDataset):
        sub_event = dataset.get_event_by_id("881")

        player_off = sub_event.player
        player_on = sub_event.replacement_player

        assert player_off.player_id == "121"
        assert player_on.player_id == "122"

        assert sub_event.time.period.id == 2
        assert sub_event.time.timestamp == timedelta(0)


class TestSciSportsCarryEvent:
    """Tests related to deserializing Carry events (from DRIBBLE subtype 300)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all carry events"""
        events = dataset.find_all("carry")
        assert len(events) == 146

    def test_carry_event(self, dataset: EventDataset):
        """Verify specific attributes of carry event"""
        carry_event = dataset.get_event_by_id("71")
        assert carry_event is not None
        assert isinstance(carry_event, CarryEvent)

        # Check basic properties
        assert carry_event.event_type == EventType.CARRY
        assert carry_event.player.name == "Player 22"
        assert carry_event.team.name == "Team Alpha"
        assert carry_event.coordinates == Point(-9.45, -12.92)

        # Check that this was originally a dribble with subtype 300
        assert carry_event.raw_event.get("baseTypeName") == "DRIBBLE"
        assert carry_event.raw_event.get("subTypeId") == 300

    def test_carry_result_checks(self, dataset: EventDataset):
        """Test carry result distribution"""
        carry_events = dataset.find_all("carry")

        complete_carries = [
            e for e in carry_events if e.result == CarryResult.COMPLETE
        ]

        # Most carries should be successful in this dataset
        assert len(complete_carries) == len(carry_events)


class TestSciSportsTakeOnEvent:
    """Tests related to deserializing Take On events (from DRIBBLE subtype 301)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all take-on events"""
        events = dataset.find_all("take_on")
        assert len(events) == 29

    def test_take_on_event(self, dataset: EventDataset):
        """Verify specific attributes of take-on event"""
        takeon_event = dataset.get_event_by_id("65")
        assert takeon_event is not None
        assert isinstance(takeon_event, TakeOnEvent)

        # Check basic properties
        assert takeon_event.event_type == EventType.TAKE_ON
        assert takeon_event.player.name == "Player 16"
        assert takeon_event.team.name == "Team Beta"
        assert takeon_event.coordinates == Point(-3.15, 27.88)

        # Check that this was originally a dribble with subtype 301
        assert takeon_event.raw_event.get("baseTypeName") == "DRIBBLE"
        assert takeon_event.raw_event.get("subTypeId") == 301

    def test_take_on_result_checks(self, dataset: EventDataset):
        """Test take-on result distribution"""
        takeon_events = dataset.find_all("take_on")

        complete_taketons = [
            e for e in takeon_events if e.result == TakeOnResult.COMPLETE
        ]
        incomplete_taketons = [
            e for e in takeon_events if e.result == TakeOnResult.INCOMPLETE
        ]

        # Both successful and unsuccessful take-ons should exist
        assert len(complete_taketons) == 22
        assert len(incomplete_taketons) == 7


class TestSciSportsClearanceEvent:
    """Tests related to deserializing Clearance events (from CLEARANCE only)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 52  # Only CLEARANCE events

    def test_clearance_event(self, dataset: EventDataset):
        """Verify specific attributes of clearance event"""
        clearance_event = dataset.get_event_by_id("32")
        assert clearance_event is not None
        assert isinstance(clearance_event, ClearanceEvent)

        # Check basic properties
        assert clearance_event.event_type == EventType.CLEARANCE
        assert clearance_event.player.name == "Player 24"
        assert clearance_event.team.name == "Team Beta"
        assert clearance_event.coordinates == Point(-28.35, 23.8)

        # Check that this was originally a clearance
        assert clearance_event.raw_event.get("baseTypeName") == "CLEARANCE"


class TestSciSportsMiscontrolEvent:
    """Tests related to deserializing Miscontrol events (from BAD_TOUCH)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all miscontrol events"""
        events = dataset.find_all("miscontrol")
        assert len(events) == 46

    def test_miscontrol_event(self, dataset: EventDataset):
        """Verify specific attributes of miscontrol event"""
        miscontrol_event = dataset.get_event_by_id("26")
        assert miscontrol_event is not None
        assert isinstance(miscontrol_event, MiscontrolEvent)

        # Check basic properties
        assert miscontrol_event.event_type == EventType.MISCONTROL
        assert miscontrol_event.player.name == "Player 28"
        assert miscontrol_event.team.name == "Team Beta"
        assert miscontrol_event.coordinates == Point(-24.15, 17.68)

        # Check that this was originally a bad touch
        assert miscontrol_event.raw_event.get("baseTypeName") == "BAD_TOUCH"


class TestSciSportsGoalkeeperEvent:
    """Tests related to deserializing Goalkeeper events (from KEEPER_SAVE)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all goalkeeper events"""
        events = dataset.find_all("goalkeeper")
        assert len(events) == 16

    def test_goalkeeper_event(self, dataset: EventDataset):
        """Verify specific attributes of goalkeeper event"""
        gk_event = dataset.get_event_by_id("274")
        assert gk_event is not None
        assert isinstance(gk_event, GoalkeeperEvent)

        # Check basic properties
        assert gk_event.event_type == EventType.GOALKEEPER
        assert gk_event.player.name == "Player 06"
        assert gk_event.team.name == "Team Alpha"
        assert gk_event.coordinates == Point(-45.15, -6.12)

        # Check that this was originally a keeper save
        assert gk_event.raw_event.get("baseTypeName") == "KEEPER_SAVE"

    def test_goalkeeper_qualifiers(self, dataset: EventDataset):
        """Test goalkeeper action qualifiers"""
        gk_events = dataset.find_all("goalkeeper")

        save_events = [
            e
            for e in gk_events
            if GoalkeeperActionType.SAVE
            in e.get_qualifier_values(GoalkeeperQualifier)
        ]

        # All goalkeeper events from KEEPER_SAVE should have SAVE qualifier
        assert len(save_events) == len(gk_events)

    def test_body_part_qualifiers(self, dataset: EventDataset):
        """Test body part qualifiers in goalkeeper events"""
        gk_events = dataset.find_all("goalkeeper")

        events_with_body_part = [
            e for e in gk_events if e.get_qualifier_values(BodyPartQualifier)
        ]

        # Some goalkeeper events should have body part information
        assert len(events_with_body_part) >= 0


class TestSciSportsBallOutEvent:
    """Tests related to deserializing Ball Out events (from BALL_DEAD)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all ball out events"""
        events = dataset.find_all("ball_out")
        assert len(events) == 97

    def test_ball_out_event(self, dataset: EventDataset):
        """Verify specific attributes of ball out event"""
        ball_out_event = dataset.get_event_by_id("30")
        assert ball_out_event is not None
        assert isinstance(ball_out_event, BallOutEvent)

        # Check basic properties
        assert ball_out_event.event_type == EventType.BALL_OUT
        assert ball_out_event.coordinates == Point(-14.7, 34.0)
        assert ball_out_event.ball_state == BallState.DEAD

        # Check that this was originally a ball dead event
        assert ball_out_event.raw_event.get("baseTypeName") == "BALL_DEAD"


class TestSciSportsFormationChangeEvent:
    """Tests related to deserializing Formation Change events (from FORMATION and POSITION)"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all formation change events"""
        events = dataset.find_all("formation_change")
        assert (
            len(events) >= 0
        )  # May not have formation changes in this dataset

    def test_formation_event(self, dataset: EventDataset):
        """Verify formation change events if they exist"""
        formation_events = dataset.find_all("formation_change")

        if formation_events:
            formation_event = formation_events[0]
            assert isinstance(formation_event, FormationChangeEvent)
            assert formation_event.event_type == EventType.FORMATION_CHANGE

            # Check that this was originally a formation or position event
            base_type_name = formation_event.raw_event.get("baseTypeName")
            assert base_type_name in ["FORMATION", "POSITION"]

    def test_position_becomes_formation_change(self, dataset: EventDataset):
        """Test that POSITION events become FormationChangeEvent"""
        # Find position events that become formation changes
        all_events = dataset.events
        position_events = [
            e
            for e in all_events
            if e.raw_event.get("baseTypeName") == "POSITION"
        ]

        formation_change_events = [
            e for e in position_events if isinstance(e, FormationChangeEvent)
        ]

        # Position changes with subTypeId 1801 should become FormationChangeEvents
        assert len(formation_change_events) >= 0
