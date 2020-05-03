from abc import ABC, abstractmethod
from typing import Tuple, Dict

from kloppy.infra.utils import Readable
from kloppy.domain import EventDataSet


class EventDataSerializer(ABC):
    @abstractmethod
    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> EventDataSet:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, data_set: EventDataSet) -> Tuple[str, str]:
        raise NotImplementedError
