import os

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
)

from kloppy import opta


class TestOpta:
    """"""

    @pytest.fixture
    def f24_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/opta_f24.xml"

    @pytest.fixture
    def f7_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/opta_f7.xml"

    def test_correct_deserialization(self, f7_data: str, f24_data: str):
        dataset = opta.load(
            f24_data=f24_data, f7_data=f7_data, coordinates="opta"
        )

        assert dataset.metadata.provider == Provider.OPTA
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 21
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

    def test_correct_normalized_deserialization(
        self, f7_data: str, f24_data: str
    ):
        dataset = opta.load(
            f24_data=f24_data,
            f7_data=f7_data,
        )
        assert dataset.events[0].coordinates == Point(0.501, 0.506)
