import os

import pytest

from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    SetPieceType,
    BodyPart,
    DatasetType,
)

from kloppy import sportec


class TestSportecEvent:
    """"""

    @pytest.fixture
    def event_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/sportec_events.xml"

    @pytest.fixture
    def meta_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/sportec_meta.xml"

    def test_correct_deserialization(self, event_data: str, meta_data: str):
        dataset = sportec.load(
            event_data=event_data, meta_data=meta_data, coordinates="sportec"
        )

        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        assert len(dataset.events) == 28
        assert dataset.metadata.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=1591381800.21,
            end_timestamp=1591384584.0,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=1591385607.01,
            end_timestamp=1591388598.0,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "DFL-OBJ-00001D"
        assert player.jersey_no == 1
        assert str(player) == "A. Schwolow"
        assert player.position.position_id is None
        assert player.position.name == "TW"

        # Check the qualifiers
        assert dataset.events[25].qualifiers[0].value == SetPieceType.KICK_OFF
        assert dataset.events[16].qualifiers[0].value == BodyPart.RIGHT_FOOT
        assert dataset.events[24].qualifiers[0].value == BodyPart.LEFT_FOOT
        assert dataset.events[26].qualifiers[0].value == BodyPart.HEAD

        assert dataset.events[0].coordinates == Point(56.41, 68.0)

    def test_correct_normalized_deserialization(
        self, event_data: str, meta_data: str
    ):
        dataset = sportec.load(event_data=event_data, meta_data=meta_data)

        assert dataset.events[0].coordinates == Point(0.5640999999999999, 1)
