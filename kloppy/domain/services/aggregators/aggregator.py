from abc import ABC, abstractmethod
from typing import List, NamedTuple

from kloppy.domain import EventDataset


class EventDatasetAggregator(ABC):
    @abstractmethod
    def aggregate(self, dataset: EventDataset) -> List[NamedTuple]:
        raise NotImplementedError
