from abc import ABC, abstractmethod
from typing import Tuple, Dict, Generic, TypeVar

from kloppy.utils import Readable
from kloppy.domain import CodeDataset


T = TypeVar("T")


class CodeDataDeserializer(ABC, Generic[T]):
    @abstractmethod
    def deserialize(self, inputs: T) -> CodeDataset:
        raise NotImplementedError


class CodeDataSerializer(ABC):
    @abstractmethod
    def serialize(self, dataset: CodeDataset) -> bytes:
        raise NotImplementedError
