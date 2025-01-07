from abc import ABC, abstractmethod
from typing import List, NamedTuple

from kloppy.domain import EventDataset, Event


class EventDatasetDeduducer(ABC):
    @abstractmethod
    def deduce(self, dataset: EventDataset) -> EventDataset:
        raise NotImplementedError
