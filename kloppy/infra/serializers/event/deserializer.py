from abc import ABC, abstractmethod
from typing import Optional, List, Generic, TypeVar, Union

from kloppy.domain import (
    EventDataset,
    Event,
    EventType,
    DatasetTransformer,
    Provider,
    EventFactory,
    DatasetType,
    DatasetTransformerBuilder,
)

T = TypeVar("T")


class EventDataDeserializer(ABC, Generic[T]):
    def __init__(
        self,
        event_types: Optional[List[Union[EventType, str]]] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        event_factory: Optional[EventFactory] = None,
    ):
        if not event_types:
            event_types = []

        self.event_types = [
            EventType[event_type.upper()]
            if isinstance(event_type, str)
            else event_type
            for event_type in event_types
        ]

        self.transformer_builder = DatasetTransformerBuilder(coordinate_system)

        if not event_factory:
            event_factory = EventFactory()
        self.event_factory = event_factory

    def should_include_event(self, event: Event) -> bool:
        if not self.event_types:
            return True
        return event.event_type in self.event_types

    def get_transformer(
        self, length: float, width: float, provider: Optional[Provider] = None
    ) -> DatasetTransformer:
        return self.transformer_builder.build(
            length=length,
            width=width,
            provider=provider or self.provider,
            dataset_type=DatasetType.EVENT,
        )

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, inputs: T) -> EventDataset:
        raise NotImplementedError
