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
    Point3D,
)

from kloppy.domain.models.event import EventType, FormationType

from kloppy import opta


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
        assert len(dataset.events) == 30
        assert len(dataset.metadata.periods) == 2
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

        assert dataset.events[0].coordinates == Point(50.1, 49.4)

        # Check the qualifiers
        assert (
            dataset.events[0].qualifiers[0].value == SetPieceType.KICK_OFF
        )  # 1510681159
        assert (
            dataset.events[6].qualifiers[0].value == BodyPart.HEAD
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
        assert (
            dataset.events[7].get_qualifier_values(DuelQualifier)[1].value
            == DuelType.AERIAL
        )
        assert (
            dataset.events[8].get_qualifier_values(DuelQualifier)[1].value
            == DuelType.GROUND
        )

        # Check event formations
        assert (
            dataset.events[5].formation == FormationType.FOUR_FOUR_TWO
            and dataset.events[5].opponent_formation
            == FormationType.FOUR_THREE_THREE
        )
        assert (
            dataset.events[6].formation == FormationType.FOUR_THREE_THREE
            and dataset.events[6].opponent_formation
            == FormationType.FOUR_FOUR_TWO
        )

    def test_shot(self, f7_data: str, f24_data: str):
        dataset = opta.load(
            f24_data=f24_data,
            f7_data=f7_data,
            event_types=["shot"],
            coordinates="opta",
        )
        assert len(dataset.events) == 2

        shot = dataset.get_event_by_id("2318695229")
        # A shot event should have a result
        assert shot.result == ShotResult.GOAL
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(100.0, 47.8, 2.5)
        # A shot event should have a body part
        assert (
            shot.get_qualifier_value(BodyPartQualifier) == BodyPart.LEFT_FOOT
        )

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
