from abc import ABC, abstractmethod
from typing import NamedTuple

from kloppy.domain import EventDataset


class EventDatasetAggregator(ABC):
    @abstractmethod
    def aggregate(self, dataset: EventDataset) -> list[NamedTuple]:
        raise NotImplementedError
