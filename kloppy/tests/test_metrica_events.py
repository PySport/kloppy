import os

import pytest

from kloppy import metrica
from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    SetPieceType,
    BodyPart,
)
from kloppy.domain.models.common import DatasetType


class TestMetricaEvents:
    @pytest.fixture
    def meta_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/epts_metrica_metadata.xml"

    @pytest.fixture
    def event_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/metrica_events.json"

    def test_correct_deserialization(self, event_data: str, meta_data: str):
        dataset = metrica.load_event(
            event_data=event_data, meta_data=meta_data
        )

        assert dataset.metadata.provider == Provider.METRICA
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 3684
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation is None
        assert dataset.metadata.teams[0].name == "Team A"
        assert dataset.metadata.teams[1].name == "Team B"

        player = dataset.metadata.teams[0].players[10]
        assert player.player_id == "Track_11"
        assert player.jersey_no == 11
        assert str(player) == "Track_11"
        assert player.position.name == "Goalkeeper"

        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=14.44,
            end_timestamp=2783.76,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=2803.6,
            end_timestamp=5742.12,
            attacking_direction=AttackingDirection.NOT_SET,
        )

        assert dataset.events[1].coordinates.x == 0.50125

        # Check the qualifiers
        assert dataset.records[1].qualifiers[0].value == SetPieceType.KICK_OFF
        assert dataset.records[100].qualifiers[0].value == BodyPart.HEAD
