import math
from datetime import datetime, timezone, timedelta

import pytest

from kloppy.domain import (
    AttackingDirection,
    BallState,
    BodyPart,
    BodyPartQualifier,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    CounterAttackQualifier,
    DatasetFlag,
    DatasetType,
    Dimension,
    DuelQualifier,
    DuelType,
    EventDataset,
    EventType,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    Orientation,
    PassQualifier,
    PassType,
    PitchDimensions,
    Point,
    Point,
    Point3D,
    Position,
    Provider,
    Score,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    build_coordinate_system,
)
from kloppy import opta
from kloppy.infra.serializers.event.opta.deserializer import (
    _get_end_coordinates,
    _parse_f24_datetime,
)


@pytest.fixture(scope="module")
def dataset(base_dir) -> EventDataset:
    """Load Opta data for FC København - FC Nordsjælland"""
    dataset = opta.load(
        f7_data=base_dir / "files" / "opta_f7.xml",
        f24_data=base_dir / "files" / "opta_f24.xml",
        coordinates="opta",
    )
    assert dataset.dataset_type == DatasetType.EVENT
    return dataset


def test_parse_f24_datetime():
    """Test if the F24 datetime is correctly parsed"""
    # timestamps have millisecond precision
    assert _parse_f24_datetime("2018-09-23T15:02:13.608") == datetime(
        2018, 9, 23, 15, 2, 13, 608000, tzinfo=timezone.utc
    )
    # milliseconds are not left-padded
    assert _parse_f24_datetime("2018-09-23T15:02:14.39") == datetime(
        2018, 9, 23, 15, 2, 14, 39000, tzinfo=timezone.utc
    )


class TestOptaMetadata:
    """Tests related to deserializing metadata (i.e., the F7 feed)"""

    def test_provider(self, dataset):
        """It should set the Opta provider"""
        assert dataset.metadata.provider == Provider.OPTA

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
        assert dataset.metadata.teams[0].name == "FC København"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-4-2"
        )
        assert dataset.metadata.teams[1].name == "FC Nordsjælland"
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-3-3"
        )
        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("111319")
        assert player.player_id == "111319"
        assert player.jersey_no == 21
        assert str(player) == "Jesse Joronen"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        # Starting players have a position
        player = dataset.metadata.teams[0].get_player_by_id("111319")
        assert player.position == Position(
            position_id="1", name="Goalkeeper", coordinates=None
        )
        assert player.starting

        # Substituted players have a "Substitute" position
        sub_player = dataset.metadata.teams[0].get_player_by_id("88022")
        assert sub_player.position == Position(
            position_id="0", name="Substitute", coordinates=None
        )
        assert not sub_player.starting

    def test_periods(self, dataset):
        """It should create the periods"""
        assert len(dataset.metadata.periods) == 5
        assert dataset.metadata.periods[0].id == 1
        period_starts = [
            _parse_f24_datetime("2018-09-23T15:02:13.608"),
            _parse_f24_datetime("2018-09-23T16:05:28.873"),
            _parse_f24_datetime("2018-09-23T17:50:01.810"),
            _parse_f24_datetime("2018-09-23T18:35:01.810"),
            _parse_f24_datetime("2018-09-23T19:05:01.810"),
        ]
        period_ends = [
            _parse_f24_datetime("2018-09-23T15:48:21.222"),
            _parse_f24_datetime("2018-09-23T16:55:37.788"),
            _parse_f24_datetime("2018-09-23T18:20:01.810"),
            _parse_f24_datetime("2018-09-23T18:50:01.810"),
            _parse_f24_datetime("2018-09-23T19:25:01.810"),
        ]
        for i, period in enumerate(dataset.metadata.periods):
            assert period.id == i + 1
            assert period.start_timestamp == period_starts[i]
            assert period.end_timestamp == period_ends[i]

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        assert dataset.metadata.pitch_dimensions == PitchDimensions(
            x_dim=Dimension(0, 100), y_dim=Dimension(0, 100)
        )

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        assert dataset.metadata.coordinate_system == build_coordinate_system(
            Provider.OPTA, width=100, length=100
        )

    def test_score(self, dataset):
        """It should set the correct score"""
        assert dataset.metadata.score == Score(home=2, away=1)

    def test_flags(self, dataset):
        """It should set the correct flags"""
        assert (
            dataset.metadata.flags
            == DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE
        )


class TestOptaEvent:
    """Generic tests related to deserializing events (i.e., the F24 feed)"""

    def test_generic_attributes(self, dataset: EventDataset):
        """Test generic event attributes"""
        event = dataset.get_event_by_id("1510681159")
        assert event.event_id == "1510681159"
        assert event.team.name == "FC København"
        assert event.ball_owning_team.name == "FC København"
        assert event.player.full_name == "Dame N'Doye"
        assert event.coordinates == Point(50.1, 49.4)
        assert event.raw_event.attrib["id"] == "1510681159"
        assert event.related_event_ids == []
        assert event.period.id == 1
        assert event.timestamp == (
            _parse_f24_datetime("2018-09-23T15:02:14.39")  # event timestamp
            - _parse_f24_datetime("2018-09-23T15:02:13.608")  # period start
        )
        assert event.ball_state == BallState.ALIVE

    def test_timestamp(self, dataset):
        """It should set the correct timestamp, reset to zero after each period"""
        kickoff_p1 = dataset.get_event_by_id("1510681159")
        assert kickoff_p1.timestamp == timedelta(seconds=0.431)
        kickoff_p2 = dataset.get_event_by_id("1209571018")
        assert kickoff_p2.timestamp == timedelta(seconds=1.557)

    def test_correct_normalized_deserialization(self, base_dir):
        """Test if the normalized deserialization is correct"""
        dataset = opta.load(
            f7_data=base_dir / "files" / "opta_f7.xml",
            f24_data=base_dir / "files" / "opta_f24.xml",
        )
        event = dataset.get_event_by_id("1510681159")
        assert event.coordinates == Point(0.501, 0.506)

    def test_ball_owning_team(self, dataset: EventDataset):
        """Test if the ball owning team is correctly set"""
        assert (
            dataset.get_event_by_id("1594254267").ball_owning_team
            == dataset.metadata.teams[1]
        )
        assert (
            dataset.get_event_by_id("2087733359").ball_owning_team
            == dataset.metadata.teams[0]
        )

    def test_setpiece_qualifiers(self, dataset: EventDataset):
        """Test if the qualifiers are correctly deserialized"""
        kick_off = dataset.get_event_by_id("1510681159")
        assert (
            kick_off.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )

    def test_body_part_qualifiers(self, dataset: EventDataset):
        """Test if the body part qualifiers are correctly deserialized"""
        header = dataset.get_event_by_id("1101592119")
        assert BodyPart.HEAD in header.get_qualifier_values(BodyPartQualifier)

    def test_card_qualifiers(self, dataset: EventDataset):
        """Test if the card qualifiers are correctly deserialized"""
        red_card = dataset.get_event_by_id("2318454729")
        assert red_card.get_qualifier_value(CardQualifier) == CardType.RED

    def test_counter_attack_qualifiers(self, dataset: EventDataset):
        """Test if the counter attack qualifiers are correctly deserialized"""
        counter_attack = dataset.get_event_by_id("2318695229")
        assert (
            counter_attack.get_qualifier_value(CounterAttackQualifier) is True
        )


class TestOptaPassEvent:
    """Tests related to deserialzing pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("pass")
        assert len(events) == 14

    def test_receiver_coordinates(self, dataset: EventDataset):
        """Test if the receiver coordinates are correctly deserialized"""
        # Check receiver coordinates for incomplete passes
        incomplete_pass = dataset.get_event_by_id("1101592119")
        assert incomplete_pass.receiver_coordinates.x == 45.5
        assert incomplete_pass.receiver_coordinates.y == 68.2

    def test_end_coordinates(self, dataset: EventDataset):
        """Test if the end coordinates are correctly deserialized"""
        pass_event = dataset.get_event_by_id("2360555167")
        assert pass_event.receiver_coordinates.x == 89.3

    def test_pass_qualifiers(self, dataset: EventDataset):
        """Test if the pass type qualfiers are correctly deserialized"""
        through_ball = dataset.get_event_by_id("1101592119")
        assert PassType.THROUGH_BALL in through_ball.get_qualifier_values(
            PassQualifier
        )
        chipped_pass = dataset.get_event_by_id("1444075194")
        assert PassType.CHIPPED_PASS in chipped_pass.get_qualifier_values(
            PassQualifier
        )


class TestOptaClearanceEvent:
    """Tests related to deserialzing clearance events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 2

    def test_correct_deserialization(self, dataset: EventDataset):
        """Test if the clearance event is correctly deserialized"""
        clearance = dataset.get_event_by_id("2498907287")
        assert clearance.event_type == EventType.CLEARANCE


class TestOptaShotEvent:
    """Tests related to deserialzing shot events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("shot")
        assert len(events) == 3

    def test_correct_deserialization(self, dataset: EventDataset):
        """Test if the shot event is correctly deserialized"""
        shot = dataset.get_event_by_id("2318695229")
        # A shot event should have a result
        assert shot.result == ShotResult.GOAL
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(100.0, 47.8, 2.5)
        # A shot event should have a body part
        assert (
            shot.get_qualifier_value(BodyPartQualifier) == BodyPart.LEFT_FOOT
        )

    def test_timestamp_goal(self, dataset: EventDataset):
        """Check timestamp from qualifier in case of goal"""
        goal = dataset.get_event_by_id("2318695229")
        assert goal.timestamp == (
            _parse_f24_datetime("2018-09-23T16:07:48.525")  # event timestamp
            - _parse_f24_datetime("2018-09-23T16:05:28.873")  # period start
        )

    def test_shot_end_coordinates(self):
        """Shots should receive the correct end coordinates."""
        # When no end coordinates are available, we return None
        assert _get_end_coordinates({}) is None

        # When a shot was not blocked, the goalmouth coordinates should be used.
        # The y- and z-coordinate are specified by qualifiers; the
        # x-coordinate is 100.0 (i.e., the goal line)
        shot_on_target_qualifiers = {
            102: "52.1",  # goal mouth y-coordinate
            103: "18.4",  # goal mouth z-coordinate
        }
        assert _get_end_coordinates(shot_on_target_qualifiers) == Point3D(
            x=100.0, y=52.1, z=18.4
        )

        # When the z-coordinate is missing, we return 2D coordinates
        incomplete_shot_qualifiers = {
            102: "52.1",  # goal mouth y-coordinate
        }
        assert _get_end_coordinates(incomplete_shot_qualifiers) == Point(
            x=100, y=52.1
        )

        # When the y-coordinate is missing, we return None
        incomplete_shot_qualifiers = {
            103: "18.4",  # goal mouth z-coordinate
        }
        assert _get_end_coordinates(incomplete_shot_qualifiers) is None

        # When a shot is blocked, the end coordinates should correspond to the
        # location where the shot was blocked.
        blocked_shot_qualifiers = {
            146: "99.1",  # blocked x-coordiante
            147: "52.5",  # blocked y-coordinate
        }
        assert _get_end_coordinates(blocked_shot_qualifiers) == Point(
            x=99.1, y=52.5
        )

        # When a shot was blocked and goal mouth locations are provided too,
        # the z-coordinate of the goal mouth coordinates should be inversely
        # projected on the location where the shot was blocked
        blocked_shot_on_target_qualifiers = {
            **shot_on_target_qualifiers,
            **blocked_shot_qualifiers,
        }
        start_coordinates = Point(x=92.6, y=57.9)
        # This requires some trigonometry. We can define two
        # right-angle triangles:
        #   - a large triangle between the start coordinates and goal mouth
        #     coordinates.
        #   - an enclosed smaller triangle between the start coordinates and
        #     the location where the shot was blocked.
        # We need to compute the length of the opposite side of the small
        # triangle. Therefore, we compute:
        #   - the length of the adjacent side of the large triangle
        adj_large = math.sqrt(
            (100 - start_coordinates.x) ** 2
            + (52.1 - start_coordinates.y) ** 2
        )
        #   - the length of the adjacent side of the small triangle
        adj_small = math.sqrt(
            (99.1 - start_coordinates.x) ** 2
            + (52.5 - start_coordinates.y) ** 2
        )
        #   - the angle of the large triangle (== the angle of the small triangle)
        alpha_large = math.atan2(18.4, adj_large)
        #  - the opposite side of the small triangle
        opp_small = math.tan(alpha_large) * adj_small
        assert _get_end_coordinates(
            blocked_shot_on_target_qualifiers, start_coordinates
        ) == Point3D(x=99.1, y=52.5, z=opp_small)

    def test_own_goal(self, dataset: EventDataset):
        """Test if own goals are correctly deserialized"""
        own_goal = dataset.get_event_by_id("2318697001")
        assert own_goal.result == ShotResult.OWN_GOAL
        # Use the inverse coordinates of the goal location
        assert own_goal.result_coordinates == Point3D(0.0, 100 - 45.6, 1.9)


class TestOptaDuelEvent:
    """Tests related to deserialzing duel events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all duel events"""
        events = dataset.find_all("duel")
        assert len(events) == 3

    def test_qualifiers(self, dataset: EventDataset):
        """Test if the qualifiers are correctly deserialized"""
        aerial_duel = dataset.get_event_by_id("1274474573")
        assert DuelType.AERIAL in aerial_duel.get_qualifier_values(
            DuelQualifier
        )
        ground_duel = dataset.get_event_by_id("2140914735")
        assert DuelType.GROUND in ground_duel.get_qualifier_values(
            DuelQualifier
        )


class TestOptaGoalkeeperEvent:
    """Tests related to deserialzing goalkeeper events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all goalkeeper events"""
        events = dataset.find_all("goalkeeper")
        assert len(events) == 5

    def test_qualifiers(self, dataset: EventDataset):
        """Test if the qualifiers are correctly deserialized"""
        save = dataset.get_event_by_id("2451170467")
        assert (
            save.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )
        claim = dataset.get_event_by_id("2453149143")
        assert (
            claim.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.CLAIM
        )
        punch = dataset.get_event_by_id("2451094707")
        assert (
            punch.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.PUNCH
        )
        keeper_pick_up = dataset.get_event_by_id("2451098837")
        assert (
            keeper_pick_up.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.PICK_UP
        )
        smother = dataset.get_event_by_id("2438594253")
        assert (
            smother.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SMOTHER
        )


class TestOptaInterceptionEvent:
    """Tests related to deserialzing interception events"""

    def test_correct_deserialization(self, dataset: EventDataset):
        """Test if the interception event is correctly deserialized"""
        event = dataset.get_event_by_id("2609934569")
        assert event.event_type == EventType.INTERCEPTION


class TestOptaMiscontrolEvent:
    """Tests related to deserialzing miscontrol events"""

    def test_correct_deserialization(self, dataset: EventDataset):
        """Test if the miscontrol event is correctly deserialized"""
        event = dataset.get_event_by_id("2509132175")
        assert event.event_type == EventType.MISCONTROL
