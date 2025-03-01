from datetime import timedelta

import pytest

from kloppy import statsbomb
from kloppy.domain import (
    BallState,
    CarryResult,
    Event,
    EventDataset,
    EventFactory,
)


class TestEvent:
    """"""

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/statsbomb_event.json"

    @pytest.fixture
    def lineup_data(self, base_dir) -> str:
        return base_dir / "files/statsbomb_lineup.json"

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

        df = goals_dataset.to_df(engine="pandas")
        assert df["event_id"].to_list() == [
            "4c7c4ab1-6b9f-4504-a237-249c2e0c549f",
            "683c6752-13bc-4892-94ed-22e1c938f1f7",
            "55d71847-9511-4417-aea9-6f415e279011",
        ]

    def test_map(self, dataset: EventDataset):
        """
        Test the `map` method on a Dataset to allow chaining (filter and map)
        """
        goals_dataset = dataset.filter("shot.goal")

        assert goals_dataset.records[0].player is not None
        goals_dataset = goals_dataset.map(
            lambda event: event.replace(player=None)
        )

        assert [record.player for record in goals_dataset] == [
            None,
            None,
            None,
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

    def test_insert(self, dataset: EventDataset):
        new_event = EventFactory().build_carry(
            qualifiers=None,
            timestamp=timedelta(seconds=700),
            end_timestamp=timedelta(seconds=701),
            result=CarryResult.COMPLETE,
            period=dataset.metadata.periods[0],
            ball_owning_team=dataset.metadata.teams[0],
            ball_state="alive",
            event_id="test-insert-1234",
            team=dataset.metadata.teams[0],
            player=dataset.metadata.teams[0].players[0],
            coordinates=(0.2, 0.3),
            end_coordinates=(0.22, 0.33),
            raw_event=None,
        )

        # insert by position
        dataset.insert(new_event, position=3)
        assert dataset.events[3].event_id == "test-insert-1234"
        del dataset.events[3]  # Remove by index to restore the dataset

        # insert by before_event_id
        dataset.insert(new_event, before_event_id=dataset.events[100].event_id)
        assert dataset.events[100].event_id == "test-insert-1234"
        del dataset.events[100]  # Remove by index to restore the dataset

        # insert by after_event_id
        dataset.insert(new_event, after_event_id=dataset.events[305].event_id)
        assert dataset.events[306].event_id == "test-insert-1234"
        del dataset.events[306]  # Remove by index to restore the dataset

        # insert by timestamp
        dataset.insert(new_event, timestamp=new_event.timestamp)
        assert dataset.events[609].event_id == "test-insert-1234"
        del dataset.events[609]  # Remove by index to restore the dataset

        # insert using scoring function
        def insert_after_scoring_function(event: Event, dataset: EventDataset):
            if event.ball_owning_team != dataset.metadata.teams[0]:
                return 0
            if event.period != new_event.period:
                return 0
            return 1 / abs(
                event.timestamp.total_seconds()
                - new_event.timestamp.total_seconds()
            )

        dataset.insert(
            new_event, scoring_function=insert_after_scoring_function
        )
        assert dataset.events[608].event_id == "test-insert-1234"
        del dataset.events[608]  # Remove by index to restore the dataset

        # insert using scoring function
        def insert_before_scoring_function(
            event: Event, dataset: EventDataset
        ):
            if event.ball_owning_team != dataset.metadata.teams[0]:
                return 0
            if event.period != new_event.period:
                return 0
            return -1 / abs(
                event.timestamp.total_seconds()
                - new_event.timestamp.total_seconds()
            )

        dataset.insert(
            new_event, scoring_function=insert_before_scoring_function
        )
        assert dataset.events[607].event_id == "test-insert-1234"
        del dataset.events[607]  # Remove by index to restore the dataset

        def no_match_scoring_function(event: Event, dataset: EventDataset):
            return 0

        with pytest.raises(ValueError):
            dataset.insert(
                new_event, scoring_function=no_match_scoring_function
            )

        # update references
        dataset.insert(new_event, position=1)
        assert dataset.events[0].next_record.event_id == "test-insert-1234"
        assert (
            dataset.events[1].prev_record.event_id
            == dataset.events[0].event_id
        )
        assert dataset.events[1].event_id == "test-insert-1234"
        assert (
            dataset.events[1].next_record.event_id
            == dataset.events[2].event_id
        )
        assert dataset.events[2].prev_record.event_id == "test-insert-1234"

        dataset.insert(new_event, position=0)
        assert dataset.events[0].prev_record is None
        assert dataset.events[0].event_id == "test-insert-1234"
        assert (
            dataset.events[0].next_record.event_id
            == dataset.events[1].event_id
        )
        assert dataset.events[1].prev_record.event_id == "test-insert-1234"

        dataset.insert(new_event, position=len(dataset))
        assert dataset.events[-2].next_record.event_id == "test-insert-1234"
        assert (
            dataset.events[-1].prev_record.event_id
            == dataset.events[-2].event_id
        )
        assert dataset.events[-1].event_id == "test-insert-1234"
        assert dataset.events[-1].next_record is None
