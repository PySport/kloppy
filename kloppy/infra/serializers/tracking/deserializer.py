from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Union

from kloppy.domain import (
    Provider,
    TrackingDataset,
    build_coordinate_system,
    DatasetTransformer,
)

T = TypeVar("T")


class TrackingDataDeserializer(ABC, Generic[T]):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
    ):
        if not limit:
            limit = 0
        self.limit = limit

        if not sample_rate:
            sample_rate = 1.0
        self.sample_rate = sample_rate

        if not coordinate_system:
            coordinate_system = Provider.KLOPPY

        if isinstance(coordinate_system, str):
            coordinate_system = Provider[coordinate_system.upper()]

        self.coordinate_system = coordinate_system

    def get_transformer(
        self, length: float, width: float, provider: Optional[Provider] = None
    ) -> DatasetTransformer:
        from_coordinate_system = build_coordinate_system(
            provider or self.provider,
            length=length,
            width=width,
        )

        to_coordinate_system = build_coordinate_system(
            self.coordinate_system,
            length=length,
            width=width,
        )

        return DatasetTransformer(
            from_coordinate_system=from_coordinate_system,
            to_coordinate_system=to_coordinate_system,
        )

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, inputs: T) -> TrackingDataset:
        raise NotImplementedError
