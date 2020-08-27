import os
from itertools import groupby

from kloppy import StatsBombSerializer, add_state, to_pandas
from kloppy.domain import EventType
from kloppy.infra.utils import performance_logging


class TestStateBuilder:
    def _load_dataset(self, base_filename="statsbomb", options=None):
        base_dir = os.path.dirname(__file__)

        serializer = StatsBombSerializer()

        with open(
            f"{base_dir}/files/{base_filename}_lineup.json", "rb"
        ) as lineup_data, open(
            f"{base_dir}/files/{base_filename}_event.json", "rb"
        ) as event_data:
            dataset = serializer.deserialize(
                inputs={"lineup_data": lineup_data, "event_data": event_data},
                options=options,
            )
            return dataset

    def test_score_state_builder(self):
        dataset = self._load_dataset("statsbomb_15986")

        with performance_logging("add_state"):
            dataset_with_state = add_state(dataset, ["score", "sequence"])

        events_per_score = {}
        for score, events in groupby(
            dataset_with_state.events, lambda event: event.state["score"]
        ):
            events = list(events)
            events_per_score[str(score)] = len(events)

        assert events_per_score == {
            "0-0": 2884,
            "1-0": 711,
            "2-0": 404,
            "3-0": 3,
        }

    def test_lineup_state_builder(self):
        dataset = self._load_dataset("statsbomb_15986")

        with performance_logging("add_state"):
            dataset_with_state = add_state(dataset, ["lineup"])

        last_events = []
        for lineup, events in groupby(
            dataset_with_state.events, lambda event: event.state["lineup"]
        ):
            events = list(events)
            last_events.append((events[-1].event_type, len(lineup.players)))

        assert last_events == [
            (EventType.CARD, 22),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.SUBSTITUTION, 21),
            (EventType.GENERIC, 21)
        ]
