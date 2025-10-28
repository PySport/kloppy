import pytest

from kloppy import opta, statsbomb
from kloppy.domain import EventDataset


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


class TestExcludePenaltyShootouts:
    """Tests for excluding penalty shootout data across all providers"""

    @pytest.fixture(scope="class")
    def dataset_with_shootout(self, base_dir) -> EventDataset:
        """Load Opta data including penalty shootout (period 5)"""
        return opta.load(
            f7_data=base_dir / "files" / "opta_f7.xml",
            f24_data=base_dir / "files" / "opta_f24.xml",
            coordinates="opta",
            exclude_penalty_shootouts=False,
        )

    @pytest.fixture(scope="class")
    def dataset_without_shootout(self, base_dir) -> EventDataset:
        """Load Opta data excluding penalty shootout (period 5)"""
        return opta.load(
            f7_data=base_dir / "files" / "opta_f7.xml",
            f24_data=base_dir / "files" / "opta_f24.xml",
            coordinates="opta",
            exclude_penalty_shootouts=True,
        )

    def test_periods_with_shootout(self, dataset_with_shootout: EventDataset):
        """It should include all 5 periods when penalty shootouts are not excluded"""
        assert len(dataset_with_shootout.metadata.periods) == 5
        period_ids = [p.id for p in dataset_with_shootout.metadata.periods]
        assert period_ids == [1, 2, 3, 4, 5]

    def test_periods_without_shootout(
        self, dataset_without_shootout: EventDataset
    ):
        """It should only include 4 periods when penalty shootouts are excluded"""
        assert len(dataset_without_shootout.metadata.periods) == 4
        period_ids = [p.id for p in dataset_without_shootout.metadata.periods]
        assert period_ids == [1, 2, 3, 4]
        # Ensure period 5 is not present
        assert 5 not in period_ids

    def test_events_with_shootout(self, dataset_with_shootout: EventDataset):
        """It should include penalty shootout events when not excluded"""
        period_5_events = [
            e
            for e in dataset_with_shootout.events
            if e.period and e.period.id == 5
        ]
        # The test file has 1 parsed penalty shootout event (a shot)
        # Note: There are 5 events with period_id="5" in the XML, but only
        # events that are currently supported by the parser are deserialized
        assert len(period_5_events) == 1

    def test_events_without_shootout(
        self, dataset_without_shootout: EventDataset
    ):
        """It should exclude all penalty shootout events when excluded"""
        period_5_events = [
            e
            for e in dataset_without_shootout.events
            if e.period and e.period.id == 5
        ]
        assert len(period_5_events) == 0

    def test_event_count_difference(
        self,
        dataset_with_shootout: EventDataset,
        dataset_without_shootout: EventDataset,
    ):
        """It should have exactly 1 fewer event when penalty shootouts are excluded"""
        count_with = len(dataset_with_shootout.events)
        count_without = len(dataset_without_shootout.events)
        # The difference is 1 because only 1 penalty shootout event is parsed
        assert count_with - count_without == 1

    def test_player_positions_without_shootout(
        self, dataset_without_shootout: EventDataset
    ):
        """It should not have any player positions referencing period 5"""
        for team in dataset_without_shootout.metadata.teams:
            for player in team.players:
                if player.positions.items:
                    for time in player.positions.items.keys():
                        assert (
                            time.period is None or time.period.id != 5
                        ), f"Player {player.full_name} has position at period 5"

    def test_team_formations_without_shootout(
        self, dataset_without_shootout: EventDataset
    ):
        """It should not have any team formations referencing period 5"""
        for team in dataset_without_shootout.metadata.teams:
            if team.formations.items:
                for time in team.formations.items.keys():
                    assert (
                        time.period is None or time.period.id != 5
                    ), f"Team {team.name} has formation at period 5"

    def test_period_references_without_shootout(
        self, dataset_without_shootout: EventDataset
    ):
        """It should correctly update period references after removing period 5"""
        periods = dataset_without_shootout.metadata.periods
        for i, period in enumerate(periods):
            # Check prev_period reference
            if i > 0:
                assert period.prev_period == periods[i - 1]
            else:
                assert period.prev_period is None

            # Check next_period reference
            if i < len(periods) - 1:
                assert period.next_period == periods[i + 1]
            else:
                assert period.next_period is None
