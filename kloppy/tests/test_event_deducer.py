from itertools import groupby

from kloppy.domain import (
    EventType,
    Event,
    EventDataset,
    FormationType,
    CarryEvent,
    Unit,
)
from kloppy.domain.services.state_builder.builder import StateBuilder
from kloppy.utils import performance_logging
from kloppy import statsbomb, statsperform


class TestEventDeducer:
    """"""

    def _load_dataset_statsperform(
        self, base_dir, base_filename="statsperform"
    ):
        return statsperform.load_event(
            ma1_data=base_dir / f"files/{base_filename}_event_ma1.json",
            ma3_data=base_dir / f"files/{base_filename}_event_ma3.json",
        )

    def _load_dataset_statsbomb(
        self, base_dir, base_filename="statsbomb", event_types=None
    ):
        return statsbomb.load(
            event_data=base_dir / f"files/{base_filename}_event.json",
            lineup_data=base_dir / f"files/{base_filename}_lineup.json",
            event_types=event_types,
        )

    def test_carry_deducer(self, base_dir):
        dataset_with_carries = self._load_dataset_statsbomb(base_dir)
        pitch = dataset_with_carries.metadata.pitch_dimensions
        all_statsbomb_caries = [
            carry
            for carry in dataset_with_carries.find_all("carry")
            if pitch.distance_between(
                carry.coordinates, carry.end_coordinates, Unit.METERS
            )
            >= 3
        ]

        dataset = self._load_dataset_statsbomb(
            base_dir,
            event_types=[
                event.value for event in EventType if event.value != "CARRY"
            ],
        )

        with performance_logging("deduce_events"):
            dataset.add_deduced_event(EventType.CARRY)
        carry = dataset.find("carry")
        index = dataset.events.index(carry)
        # Assert end location is equal to start location of next action
        assert carry.end_coordinates == dataset.events[index + 1].coordinates
        assert carry.player == dataset.events[index + 1].player
        all_carries = dataset.find_all("carry")
        print("Original number of carries", len(all_statsbomb_caries))
        print("Generated amount of carries", len(all_carries))
