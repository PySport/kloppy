import os
from itertools import groupby

from kloppy.domain import EventType, Event, EventDataset
from kloppy.domain.services.state_builder.builder import StateBuilder, T
from kloppy.utils import performance_logging
from kloppy import statsbomb


class TestStateBuilder:
    """"""

    def _load_dataset(self, base_filename="statsbomb"):
        base_dir = os.path.dirname(__file__)

        return statsbomb.load(
            event_data=f"{base_dir}/files/{base_filename}_event.json",
            lineup_data=f"{base_dir}/files/{base_filename}_lineup.json",
        )

    def test_score_state_builder(self):
        dataset = self._load_dataset()

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("score")

        events_per_score = {}
        for score, events in groupby(
            dataset_with_state.events, lambda event: event.state["score"]
        ):
            events = list(events)
            events_per_score[str(score)] = len(events)

        assert events_per_score == {
            "0-0": 2897,
            "1-0": 717,
            "2-0": 405,
            "3-0": 3,
        }

    def test_sequence_state_builder(self):
        dataset = self._load_dataset()

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("sequence")

        events_per_sequence = {}
        for sequence_id, events in groupby(
            dataset_with_state.events,
            lambda event: event.state["sequence"].sequence_id,
        ):
            events = list(events)
            events_per_sequence[sequence_id] = len(events)

        assert events_per_sequence[0] == 4
        assert events_per_sequence[50] == 14

    def test_lineup_state_builder(self):
        dataset = self._load_dataset("statsbomb_15986")

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("lineup")

        last_events = []
        for lineup, events in groupby(
            dataset_with_state.events, lambda event: event.state["lineup"]
        ):
            events = list(events)
            # inspect last event which changed the lineup
            last_events.append((events[-1].event_type, len(lineup.players)))

        assert last_events == [
            (EventType.CARD, 22),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.GENERIC, 21),
        ]

    def test_register_custom_builder(self):
        class CustomStateBuilder(StateBuilder):
            def initial_state(self, dataset: EventDataset) -> int:
                return 0

            def reduce_before(self, state: int, event: Event) -> int:
                return state + 1

            def reduce_after(self, state: int, event: Event) -> int:
                return state + 1

        dataset = self._load_dataset("statsbomb_15986")

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("custom")

        assert dataset_with_state.events[0].state["custom"] == 1
        assert dataset_with_state.events[1].state["custom"] == 3
        assert dataset_with_state.events[2].state["custom"] == 5
        assert dataset_with_state.events[3].state["custom"] == 7
