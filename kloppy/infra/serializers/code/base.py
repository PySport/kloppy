from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from kloppy.domain import CodeDataset


T_I = TypeVar("T_I")
T_O = TypeVar("T_O")


class CodeDataDeserializer(ABC, Generic[T_I]):
    @abstractmethod
    def deserialize(self, inputs: T_I) -> CodeDataset:
        raise NotImplementedError


class CodeDataSerializer(ABC, Generic[T_O]):
    @abstractmethod
    def serialize(self, dataset: CodeDataset, outputs: T_O) -> bool:
        raise NotImplementedError
