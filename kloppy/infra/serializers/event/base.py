from abc import ABC, abstractmethod
from typing import Tuple, Dict

from kloppy.utils import Readable
from kloppy.domain import EventDataset


class EventDataSerializer(ABC):
    @abstractmethod
    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> EventDataset:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, dataset: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
