from datetime import timedelta
from typing import Callable, Optional, TypeVar

from kloppy.domain import DataRecord, Dataset

D = TypeVar("D", bound=Dataset)  # any Dataset subclass
R = TypeVar("R", bound=DataRecord)  # record type within the dataset


def insert_record(
    dataset: D,
    record: R,
    *,
    position: Optional[int] = None,
    before_id: Optional[str] = None,
    after_id: Optional[str] = None,
    timestamp: Optional[timedelta] = None,
    scoring_function: Optional[Callable[[R, D], float]] = None,
) -> int:
    """
    Generic insertion function for any Dataset subclass.

    Returns the index where the record was inserted.
    """
    records = dataset.records  # type: ignore

    # Determine insert position
    if position is not None:
        insert_position = position
    elif before_id is not None:
        insert_position = next(
            i
            for i, r in enumerate(records)
            if getattr(r, "record_id", getattr(r, "event_id", None))
            == before_id
        )
    elif after_id is not None:
        insert_position = next(
            i + 1
            for i, r in enumerate(records)
            if getattr(r, "record_id", getattr(r, "event_id", None)) == after_id
        )
    elif timestamp is not None:
        insert_position = next(
            (
                i
                for i, r in enumerate(records)
                if getattr(r, "timestamp", None) > timestamp
            ),
            len(records),
        )
    elif scoring_function is not None:
        scores = [
            (i, scoring_function(record, dataset))
            for i, r in enumerate(records)
        ]
        best_index, best_score = max(
            scores, key=lambda x: abs(x[1]), default=(0, 0)
        )
        if best_score == 0:
            raise ValueError("No valid insertion position found.")
        insert_position = best_index + 1 if best_score > 0 else best_index
    else:
        raise ValueError("Cannot determine insertion position")

    # Insert record
    records.insert(insert_position, record)
    record.dataset = dataset  # type: ignore

    # Update references if they exist (prev/next)
    for i in range(
        max(0, insert_position - 1), min(insert_position + 2, len(records))
    ):
        if hasattr(records[i], "prev_record"):
            records[i].prev_record = records[i - 1] if i > 0 else None
        if hasattr(records[i], "next_record"):
            records[i].next_record = (
                records[i + 1] if i + 1 < len(records) else None
            )

    return insert_position
