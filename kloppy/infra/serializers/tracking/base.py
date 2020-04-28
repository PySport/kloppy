from abc import ABC, abstractmethod
from typing import Tuple, Dict

from ...utils import Readable
from ....domain.models import DataSet


class TrackingDataSerializer(ABC):
    @abstractmethod
    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> DataSet:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, data_set: DataSet) -> Tuple[str, str]:
        raise NotImplementedError
