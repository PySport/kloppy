from abc import ABC, abstractmethod
from typing import Optional

from kloppy.domain import EventDataset, EventFactory


class SyntheticEventGenerator(ABC):
    def __init__(self, event_factory: Optional[EventFactory] = None):
        if not event_factory:
            event_factory = EventFactory()
        self.event_factory = event_factory

    @abstractmethod
    def add_synthetic_event(self, dataset: EventDataset) -> EventDataset:
        raise NotImplementedError
