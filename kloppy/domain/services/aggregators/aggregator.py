from abc import ABC, abstractmethod
from typing import Dict, Any, Hashable, List, NamedTuple

from kloppy.domain import EventDataset


class EventDatasetAggregator(ABC):
    @abstractmethod
    def aggregate(self, dataset: EventDataset) -> List[NamedTuple]:
        raise NotImplementedError
