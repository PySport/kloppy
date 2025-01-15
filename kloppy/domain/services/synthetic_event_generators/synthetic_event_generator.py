from abc import ABC, abstractmethod

from kloppy.domain import EventDataset


class SyntheticEventGenerator(ABC):
    @abstractmethod
    def add_synthetic_event(self, dataset: EventDataset) -> EventDataset:
        raise NotImplementedError
