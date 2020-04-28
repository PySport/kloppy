from abc import ABC, abstractmethod
from typing import Tuple, Dict

from kloppy.infra.utils import Readable
from kloppy.domain import DataSet


class TrackingDataSerializer(ABC):
    @abstractmethod
    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> DataSet:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, data_set: DataSet) -> Tuple[str, str]:
        raise NotImplementedError
