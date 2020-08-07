import os

from kloppy import StatsBombSerializer
from kloppy.domain import (
    AttackingDirection,
    Period,
    Orientation,
    Player,
    Position,
    Provider,
)
from kloppy.domain.models.common import DatasetType


class TestStatsbomb:
    def test_correct_deserialization(self):
        """
        This test uses data from the StatsBomb open data project.
        """
        base_dir = os.path.dirname(__file__)

        serializer = StatsBombSerializer()

        with open(
            f"{base_dir}/files/statsbomb_lineup.json", "rb"
        ) as lineup_data, open(
            f"{base_dir}/files/statsbomb_event.json", "rb"
        ) as event_data:

            dataset = serializer.deserialize(
                inputs={"lineup_data": lineup_data, "event_data": event_data}
            )

        assert dataset.metadata.provider == Provider.STATSBOMB
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 4002
        assert len(dataset.metadata.periods) == 2
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        assert dataset.metadata.teams[0].name == "Barcelona"
        assert dataset.metadata.teams[1].name == "Deportivo Alavés"

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "3109"
        assert player.jersey_no == 14
        assert str(player) == "Malcom Filipe Silva de Oliveira"
        assert player.position is None  # not set

        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=0.0,
            end_timestamp=2705.267,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=2705.268,
            end_timestamp=5557.321,
            attacking_direction=AttackingDirection.NOT_SET,
        )
