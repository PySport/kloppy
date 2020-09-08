from abc import ABC, abstractmethod
from typing import Tuple, Dict

from kloppy.utils import Readable
from kloppy.domain import Dataset


class TrackingDataSerializer(ABC):
    @abstractmethod
    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> Dataset:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, dataset: Dataset) -> Tuple[str, str]:
        raise NotImplementedError
