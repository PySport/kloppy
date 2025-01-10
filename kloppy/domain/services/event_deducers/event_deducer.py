from abc import ABC, abstractmethod
from kloppy.domain import EventDataset


class EventDatasetDeduducer(ABC):
    @abstractmethod
    def deduce(self, dataset: EventDataset) -> EventDataset:
        raise NotImplementedError
