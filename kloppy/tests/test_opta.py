import math

import pytest

from kloppy.domain import (
    AttackingDirection,
    Period,
    Orientation,
    Provider,
    Ground,
    Point,
    BodyPart,
    SetPieceType,
    PassType,
    DatasetType,
    CardType,
    FormationType,
    GoalkeeperQualifier,
    GoalkeeperActionType,
    DuelQualifier,
    DuelType,
    ShotResult,
    SetPieceQualifier,
    CounterAttackQualifier,
    BodyPartQualifier,
    Point,
    Point3D,
)

from kloppy.domain.models.event import (
    EventType,
    PassQualifier,
    BodyPartQualifier,
)

from kloppy import opta
from kloppy.infra.serializers.event.opta.deserializer import (
    _get_end_coordinates,
)


class TestOpta:
    """"""

    @pytest.fixture
    def f24_data(self, base_dir) -> str:
        return base_dir / "files/opta_f24.xml"

    @pytest.fixture
    def f7_data(self, base_dir) -> str:
        return base_dir / "files/opta_f7.xml"

    def test_correct_deserialization(self, f7_data: str, f24_data: str):
        dataset = opta.load(
            f24_data=f24_data, f7_data=f7_data, coordinates="opta"
        )
        assert dataset.metadata.provider == Provider.OPTA
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 33
        assert len(dataset.metadata.periods) == 5
        assert (
            dataset.events[10].ball_owning_team == dataset.metadata.teams[1]
        )  # 1594254267
        assert (
            dataset.events[15].ball_owning_team == dataset.metadata.teams[0]
        )  # 2087733359
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        assert dataset.metadata.teams[0].name == "FC København"
        assert dataset.metadata.teams[0].ground == Ground.HOME
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-4-2"
        )
        assert dataset.metadata.teams[1].name == "FC Nordsjælland"
        assert dataset.metadata.teams[1].ground == Ground.AWAY
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-3-3"
        )

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "111319"
        assert player.jersey_no == 21
        assert str(player) == "Jesse Joronen"
        assert player.position.position_id == "1"
        assert player.position.name == "Goalkeeper"

        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=1537714933.608,
            end_timestamp=1537717701.222,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=1537718728.873,
            end_timestamp=1537721737.788,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.metadata.periods[4] == Period(
            id=5,
            start_timestamp=1537729501.81,
            end_timestamp=1537730701.81,
            attacking_direction=AttackingDirection.NOT_SET,
        )

        assert dataset.events[0].coordinates == Point(50.1, 49.4)

        # Check the qualifiers
        assert (
            dataset.events[0].qualifiers[0].value == SetPieceType.KICK_OFF
        )  # 1510681159
        assert (
            BodyPartQualifier(value=BodyPart.HEAD)
            in dataset.events[6].qualifiers
        )  # 1101592119
        assert (
            PassQualifier(value=PassType.THROUGH_BALL)
            in dataset.events[6].qualifiers
        )  # 1101592119
        assert (
            dataset.events[5].qualifiers[0].value == PassType.CHIPPED_PASS
        )  # 1444075194
        assert (
            dataset.events[19].qualifiers[0].value == CardType.RED
        )  # 2318695229
        assert (
            dataset.events[21].event_type == EventType.CLEARANCE
        )  # 2498907287

        # Check receiver coordinates for incomplete passes
        assert dataset.events[6].receiver_coordinates.x == 45.5
        assert dataset.events[6].receiver_coordinates.y == 68.2

        # Check timestamp from qualifier in case of goal
        assert dataset.events[17].timestamp == 139.65200018882751  # 2318695229
        # assert dataset.events[17].coordinates_y == 12

        # Check Own goal
        assert dataset.events[18].result.value == "OWN_GOAL"  # 2318697001
        # Check OFFSIDE pass has end_coordinates
        assert dataset.events[20].receiver_coordinates.x == 89.3  # 2360555167

        # Check goalkeeper qualifiers
        assert (
            dataset.events[23].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )
        assert (
            dataset.events[24].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.CLAIM
        )
        assert (
            dataset.events[25].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.PUNCH
        )
        assert (
            dataset.events[26].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.PICK_UP
        )
        assert (
            dataset.events[27].get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SMOTHER
        )
        assert (
            dataset.events[28].event_type == EventType.INTERCEPTION
        )  # 2609934569
        assert (
            dataset.events[29].event_type == EventType.MISCONTROL
        )  # 250913217

        # Check counterattack
        assert (
            CounterAttackQualifier(value=True) in dataset.events[17].qualifiers
        )  # 2318695229

        # Check DuelQualifiers
        assert DuelType.AERIAL in dataset.events[7].get_qualifier_values(
            DuelQualifier
        )
        assert (
            dataset.events[8].get_qualifier_values(DuelQualifier)[1]
            == DuelType.GROUND
        )

    def test_shot(self, f7_data: str, f24_data: str):
        dataset = opta.load(
            f24_data=f24_data,
            f7_data=f7_data,
            event_types=["shot"],
            coordinates="opta",
        )
        assert len(dataset.events) == 3

        shot = dataset.get_event_by_id("2318695229")
        # A shot event should have a result
        assert shot.result == ShotResult.GOAL
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(100.0, 47.8, 2.5)
        # A shot event should have a body part
        assert (
            shot.get_qualifier_value(BodyPartQualifier) == BodyPart.LEFT_FOOT
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

    def test_own_goal(self, f7_data: str, f24_data: str):
        dataset = opta.load(
            f24_data=f24_data,
            f7_data=f7_data,
            event_types=["shot"],
            coordinates="opta",
        )

        own_goal = dataset.get_event_by_id("2318697001")
        assert own_goal.result == ShotResult.OWN_GOAL
        # Use the inverse coordinates of the goal location
        assert own_goal.result_coordinates == Point3D(0.0, 100 - 45.6, 1.9)

    def test_correct_normalized_deserialization(
        self, f7_data: str, f24_data: str
    ):
        dataset = opta.load(
            f24_data=f24_data,
            f7_data=f7_data,
        )
        assert dataset.events[0].coordinates == Point(0.501, 0.506)
