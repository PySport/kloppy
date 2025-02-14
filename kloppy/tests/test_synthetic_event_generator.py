from datetime import timedelta

from kloppy.domain import (
    EventType,
    Unit,
)
from kloppy.utils import performance_logging
from kloppy import statsbomb, statsperform


class TestSyntheticEventGenerator:
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

    def calculate_carry_accuracy(
        self, real_carries, generated_carries, real_carries_with_min_length
    ):
        def is_match(real_carry, generated_carry):
            return (
                real_carry.player
                and generated_carry.player
                and real_carry.player.player_id
                == generated_carry.player.player_id
                and real_carry.period == generated_carry.period
                and abs(real_carry.timestamp - generated_carry.timestamp)
                < timedelta(seconds=5)
            )

        true_positives = 0
        matched_real_carries = set()
        for generated_carry in generated_carries:
            for idx, real_carry in enumerate(real_carries):
                if idx in matched_real_carries:
                    continue
                if is_match(real_carry, generated_carry):
                    true_positives += 1
                    matched_real_carries.add(idx)
                    break

        false_negatives = 0
        matched_generated_carries = set()
        for real_carry in real_carries_with_min_length:
            found_match = False
            for idx, generated_carry in enumerate(generated_carries):
                if idx in matched_generated_carries:
                    continue
                if is_match(real_carry, generated_carry):
                    found_match = True
                    matched_generated_carries.add(idx)
                    break
            if not found_match:
                false_negatives += 1

        false_positives = len(generated_carries) - true_positives

        accuracy = true_positives / (
            true_positives + false_positives + false_negatives
        )

        print("TP:", true_positives)
        print("FP:", false_positives)
        print("FN:", false_negatives)
        print("accuracy:", accuracy)

        return accuracy

    def test_synthetic_carry_generator(self, base_dir):
        dataset_with_carries = self._load_dataset_statsbomb(base_dir)
        pitch = dataset_with_carries.metadata.pitch_dimensions

        min_length_meters = 3
        max_length_meters = 60
        max_duration = timedelta(seconds=10)

        all_statsbomb_caries = dataset_with_carries.find_all("carry")
        all_qualifying_statsbomb_queries = [
            carry
            for carry in all_statsbomb_caries
            if (
                min_length_meters
                <= pitch.distance_between(
                    carry.coordinates, carry.end_coordinates, Unit.METERS
                )
                <= max_length_meters
                and carry.end_timestamp - carry.timestamp < max_duration
            )
        ]

        dataset = self._load_dataset_statsbomb(
            base_dir,
            event_types=[
                event.value for event in EventType if event.value != "CARRY"
            ],
        )

        with performance_logging("generating synthetic events"):
            dataset = dataset.add_synthetic_event(
                EventType.CARRY,
                min_length_meters=min_length_meters,
                max_length_meters=max_length_meters,
                max_duration=max_duration,
            )
        all_carries = dataset.find_all("carry")
        assert (
            self.calculate_carry_accuracy(
                all_statsbomb_caries,
                all_carries,
                all_qualifying_statsbomb_queries,
            )
            > 0.80
        )

    def test_synthetic_ball_receipt_generator(self, base_dir):

        dataset = self._load_dataset_statsbomb(
            base_dir,
        )

        with performance_logging("generating synthetic events"):
            dataset = dataset.add_synthetic_event(
                EventType.BALL_RECEIPT,
            )
        all_receivals = dataset.find_all("ball_receipt")
        print(dataset.to_df()[:100].to_string())
        print(len(all_receivals))
