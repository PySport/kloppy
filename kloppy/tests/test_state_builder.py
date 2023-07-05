from itertools import groupby

from kloppy.domain import EventType, Event, EventDataset, FormationType
from kloppy.domain.services.state_builder.builder import StateBuilder, T
from kloppy.utils import performance_logging
from kloppy import statsbomb


class TestStateBuilder:
    """"""

    def _load_dataset(self, base_dir, base_filename="statsbomb"):
        return statsbomb.load(
            event_data=base_dir / f"files/{base_filename}_event.json",
            lineup_data=base_dir / f"files/{base_filename}_lineup.json",
        )

    def test_score_state_builder(self, base_dir):
        dataset = self._load_dataset(base_dir)

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("score")

        events_per_score = {}
        for score, events in groupby(
            dataset_with_state.events, lambda event: event.state["score"]
        ):
            events = list(events)
            events_per_score[str(score)] = len(events)

        assert events_per_score == {
            "0-0": 2909,
            "1-0": 717,
            "2-0": 405,
            "3-0": 8,
        }

    def test_sequence_state_builder(self, base_dir):
        dataset = self._load_dataset(base_dir)

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
        assert events_per_sequence[51] == 14

    def test_lineup_state_builder(self, base_dir):
        dataset = self._load_dataset(base_dir, base_filename="statsbomb_15986")

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

    def test_formation_state_builder(self, base_dir):
        dataset = self._load_dataset(base_dir, base_filename="statsbomb")

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("formation")

        events_per_formation_change = {}
        for formation, events in groupby(
            dataset_with_state.events,
            lambda event: event.state["formation"].away,
        ):
            events = list(events)
            events_per_formation_change[str(formation)] = len(events)

        # inspect FormationChangeEvent usage and formation state_builder
        assert events_per_formation_change["4-1-4-1"] == 3085
        assert events_per_formation_change["4-4-2"] == 954

        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-4-2"
        )
        assert dataset_with_state.events[1].state[
            "formation"
        ].home == FormationType("4-4-2")

    def test_register_custom_builder(self, base_dir):
        class CustomStateBuilder(StateBuilder):
            def initial_state(self, dataset: EventDataset) -> int:
                return 0

            def reduce_before(self, state: int, event: Event) -> int:
                return state + 1

            def reduce_after(self, state: int, event: Event) -> int:
                return state + 1

        dataset = self._load_dataset(base_dir, base_filename="statsbomb_15986")

        with performance_logging("add_state"):
            dataset_with_state = dataset.add_state("custom")

        assert dataset_with_state.events[0].state["custom"] == 1
        assert dataset_with_state.events[1].state["custom"] == 3
        assert dataset_with_state.events[2].state["custom"] == 5
        assert dataset_with_state.events[3].state["custom"] == 7
