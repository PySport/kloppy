import os

import pytest


from kloppy import statsbomb
from kloppy.domain import EventDataset


class TestEvent:
    """"""

    @pytest.fixture
    def event_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsbomb_event.json"

    @pytest.fixture
    def lineup_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsbomb_lineup.json"

    @pytest.fixture()
    def dataset(self, lineup_data: str, event_data: str) -> EventDataset:
        return statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            coordinates="statsbomb",
        )

    def test_navigation(self, dataset: EventDataset):
        """
        Test navigating (next/prev) through events
        """
        passes = dataset.find_all("pass")
        assert passes[0].next("pass") == passes[1]
        assert passes[1].prev("pass") == passes[0]
        assert passes[0].next() == dataset.get_event_by_id(
            "61da36dc-d862-416c-8ee3-1a0cd24dc086"
        )

        goals = dataset.find_all("shot.goal")
        assert len(goals) == 3
        assert goals[0].prev("shot.goal") is None
        assert goals[0].next("shot.goal") == goals[1]
        assert goals[0].next("shot.goal") == goals[2].prev("shot.goal")
        assert goals[2].next("shot.goal") is None

        first_goal = dataset.find("shot.goal")
        assert first_goal == goals[0]
        assert first_goal.next(".goal") == goals[1]
        assert first_goal.next(".goal").next(".goal") == goals[2]
        assert first_goal.next(".goal").next(".goal").next(".goal") is None

    def test_filter(self, dataset: EventDataset):
        """
        Test filtering allows simple 'css selector' (<event_type>.<result>)
        """
        goals_dataset = dataset.filter("shot.goal")

        df = goals_dataset.to_pandas()
        assert df["event_id"].to_list() == [
            "4c7c4ab1-6b9f-4504-a237-249c2e0c549f",
            "683c6752-13bc-4892-94ed-22e1c938f1f7",
            "55d71847-9511-4417-aea9-6f415e279011",
        ]

    def test_find_all(self, dataset: EventDataset):
        """
        Test find_all allows simple 'css selector' (<event_type>.<result>)
        """
        goals = dataset.find_all("shot.goal")
        assert len(goals) == 3
        assert goals[0].prev("shot.goal") is None
        assert goals[0].next("shot.goal") == goals[1]
        assert goals[0].next("shot.goal") == goals[2].prev("shot.goal")
        assert goals[2].next("shot.goal") is None
