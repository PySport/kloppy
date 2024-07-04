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
        self,
        pitch_length: Optional[float] = None,
        pitch_width: Optional[float] = None,
        provider: Optional[Provider] = None,
    ) -> DatasetTransformer:
        return self.transformer_builder.build(
            provider=provider or self.provider,
            dataset_type=DatasetType.TRACKING,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
        )

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, inputs: T) -> TrackingDataset:
        raise NotImplementedError
