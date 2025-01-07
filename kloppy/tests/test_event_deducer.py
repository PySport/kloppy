from itertools import groupby

from kloppy.domain import (
    EventType,
    Event,
    EventDataset,
    FormationType,
    CarryEvent,
)
from kloppy.domain.services.state_builder.builder import StateBuilder
from kloppy.utils import performance_logging
from kloppy import statsbomb, statsperform


class TestEventDeducer:
    """"""

    def _load_dataset(self, base_dir, base_filename="statsperform"):
        return statsperform.load_event(
            ma1_data=base_dir / f"files/{base_filename}_event_ma1.json",
            ma3_data=base_dir / f"files/{base_filename}_event_ma3.json",
            coordinates="statsbomb",
        )

    def test_carry_deducer(self, base_dir):
        dataset = self._load_dataset(base_dir)

        with performance_logging("deduce_events"):
            dataset.add_deduced_event(EventType.CARRY)
        carry = dataset.find("carry")
        index = dataset.events.index(carry)
        # Assert end location is equal to start location of next action
        assert carry.end_coordinates == dataset.events[index + 1].coordinates
        assert carry.player == dataset.events[index + 1].player
