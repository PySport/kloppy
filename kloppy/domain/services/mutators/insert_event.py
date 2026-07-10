from datetime import timedelta
from typing import Callable

from kloppy.domain import Event, EventDataset

from .base import DatasetMutator
from .helpers.insert import insert_record


class EventDatasetInsertMutator(DatasetMutator[EventDataset]):
    def __init__(
        self,
        event: Event,
        *,
        position: int | None = None,
        before_event_id: str | None = None,
        after_event_id: str | None = None,
        timestamp: timedelta | None = None,
        scoring_function: Callable[[Event, EventDataset], float] | None = None,
        inplace: bool = False,
    ):
        super().__init__(inplace=inplace)
        self.event = event
        self.position = position
        self.before_event_id = before_event_id
        self.after_event_id = after_event_id
        self.timestamp = timestamp
        self.scoring_function = scoring_function

    def _mutate_inplace(self, dataset: EventDataset) -> EventDataset:
        insert_record(
            dataset,
            self.event,
            position=self.position,
            before_event_id=self.before_event_id,
            after_event_id=self.after_event_id,
            timestamp=self.timestamp,
            scoring_function=self.scoring_function,
        )
        return dataset
