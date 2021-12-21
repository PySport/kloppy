import os

import pytest

from kloppy.domain import (
    AttackingDirection,
    Ground,
    Orientation,
    Period,
    Point,
    Provider,
    SetPieceType,
    DatasetType,
)

from kloppy import datafactory


class TestDatafactory:
    @pytest.fixture
    def event_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/datafactory_events.json"

    def test_correct_deserialization(self, event_data: str):
        dataset = datafactory.load(
            event_data=event_data, coordinates="datafactory"
        )

        assert dataset.metadata.provider == Provider.DATAFACTORY
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 1027
        assert len(dataset.metadata.periods) == 2
        assert dataset.events[10].ball_owning_team == dataset.metadata.teams[1]
        assert dataset.events[23].ball_owning_team == dataset.metadata.teams[0]
        assert dataset.metadata.orientation == Orientation.HOME_TEAM
        assert dataset.metadata.teams[0].name == "Team A"
        assert dataset.metadata.teams[0].ground == Ground.HOME
        assert dataset.metadata.teams[1].name == "Team B"
        assert dataset.metadata.teams[1].ground == Ground.AWAY

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "38804"
        assert player.jersey_no == 1
        assert str(player) == "Daniel Bold"
        assert player.position is None  # not set
        assert player.starting

        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=0,
            end_timestamp=2912,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=2700,
            end_timestamp=5710,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        assert dataset.events[0].coordinates == Point(0.01, 0.01)

        # Check the qualifiers
        assert dataset.events[0].qualifiers[0].value == SetPieceType.KICK_OFF
        assert dataset.events[412].qualifiers[0].value == SetPieceType.THROW_IN

    def test_correct_normalized_deserialization(self, event_data: str):
        dataset = datafactory.load(event_data=event_data)

        assert dataset.events[0].coordinates == Point(0.505, 0.505)
