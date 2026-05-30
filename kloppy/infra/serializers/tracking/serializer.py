from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from kloppy.domain import Provider, TrackingDataset

T = TypeVar("T")


class TrackingDataSerializer(ABC, Generic[T]):
    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def serialize(self, dataset: TrackingDataset, outputs: T) -> bool:
        raise NotImplementedError
