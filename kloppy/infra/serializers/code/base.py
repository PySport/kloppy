from abc import ABC, abstractmethod
from typing import Tuple, Dict

from kloppy.utils import Readable
from kloppy.domain import CodeDataset


class CodeDataSerializer(ABC):
    @abstractmethod
    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> CodeDataset:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, dataset: CodeDataset) -> bytes:
        raise NotImplementedError
