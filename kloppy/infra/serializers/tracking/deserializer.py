from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Union

from kloppy.domain import (
    Provider,
    TrackingDataset,
    DatasetTransformer,
    DatasetTransformerBuilder,
    DatasetType,
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

        self.transformer_builder = DatasetTransformerBuilder(coordinate_system)

    def get_transformer(
        self, length: float, width: float, provider: Optional[Provider] = None
    ) -> DatasetTransformer:
        return self.transformer_builder.build(
            length=length,
            width=width,
            provider=provider or self.provider,
            dataset_type=DatasetType.TRACKING,
        )

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, inputs: T) -> TrackingDataset:
        raise NotImplementedError
