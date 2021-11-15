import os

import pytest

from kloppy.domain import (
    AttackingDirection,
    Period,
    Orientation,
    Provider,
    Point,
    BodyPartQualifier,
    BodyPart,
    DatasetType,
)

from kloppy import statsbomb


class TestStatsbomb:
    """"""

    @pytest.fixture
    def event_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsbomb_event.json"

    @pytest.fixture
    def lineup_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsbomb_lineup.json"

    def test_correct_deserialization(self, lineup_data: str, event_data: str):
        """
        This test uses data from the StatsBomb open data project.
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            coordinates="statsbomb",
        )

        assert dataset.metadata.provider == Provider.STATSBOMB
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 4022
        assert len(dataset.metadata.periods) == 2
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        assert dataset.metadata.teams[0].name == "Barcelona"
        assert dataset.metadata.teams[1].name == "Deportivo Alavés"

        player = dataset.metadata.teams[0].get_player_by_id("5503")
        assert player.player_id == "5503"
        assert player.jersey_no == 10
        assert str(player) == "Lionel Andrés Messi Cuccittini"
        assert player.position is None  # not set
        assert player.starting

        sub_player = dataset.metadata.teams[0].get_player_by_id("3501")
        assert str(sub_player) == "Philippe Coutinho Correia"
        assert not sub_player.starting

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

        assert dataset.events[10].coordinates == Point(34.5, 20.5)

        assert (
            dataset.events[791].get_qualifier_value(BodyPartQualifier)
            == BodyPart.HEAD
        )

        assert (
            dataset.events[2231].get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )

        assert (
            dataset.events[195].get_qualifier_value(BodyPartQualifier) is None
        )

    def test_correct_normalized_deserialization(
        self, lineup_data: str, event_data: str
    ):
        """
        This test uses data from the StatsBomb open data project.
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data, event_data=event_data
        )

        assert dataset.events[10].coordinates == Point(0.2875, 0.25625)

    def test_substitution(self, lineup_data: str, event_data: str):
        """
        Test substitution events
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            event_types=["substitution"],
        )

        assert len(dataset.events) == 6

        subs = [
            (6374, 3501),
            (6839, 6935),
            (6581, 6566),
            (6613, 6624),
            (5477, 11392),
            (5203, 8206),
        ]

        for event_idx, (player_id, replacement_player_id) in enumerate(subs):
            event = dataset.events[event_idx]
            assert event.player == event.team.get_player_by_id(player_id)
            assert event.replacement_player == event.team.get_player_by_id(
                replacement_player_id
            )
