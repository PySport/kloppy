from abc import ABC, abstractmethod
from dataclasses import fields, replace
from typing import Any, Generic, Optional, TypeVar, Union
import warnings

from kloppy.domain import (
    DatasetTransformer,
    DatasetTransformerBuilder,
    DatasetType,
    Event,
    EventDataset,
    EventFactory,
    EventType,
    Provider,
)

T = TypeVar("T")


class EventDataDeserializer(ABC, Generic[T]):
    def __init__(
        self,
        event_types: Optional[list[Union[EventType, str]]] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        event_factory: Optional[EventFactory] = None,
    ):
        if not event_types:
            event_types = []

        self.event_types = [
            (
                EventType[event_type.upper()]
                if isinstance(event_type, str)
                else event_type
            )
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
        self,
        pitch_length: Optional[float] = None,
        pitch_width: Optional[float] = None,
        provider: Optional[Provider] = None,
    ) -> DatasetTransformer:
        return self.transformer_builder.build(
            provider=provider or self.provider,
            dataset_type=DatasetType.EVENT,
            pitch_length=pitch_length,
            pitch_width=pitch_width,
        )

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def _deserialize(self, inputs: T) -> EventDataset:
        raise NotImplementedError

    def deserialize(
        self, inputs: T, additional_metadata: Optional[dict[str, Any]] = None
    ) -> EventDataset:
        dataset = self._deserialize(inputs)

        # Check for additional metadata to merge
        if additional_metadata:
            # Identify valid fields in the Metadata class
            valid_fields = {f.name for f in fields(dataset.metadata)}

            # Split additional_metadata into known and unknown keys
            known_updates = {}
            unknown_updates = {}

            for key, value in additional_metadata.items():
                if key in valid_fields:
                    known_updates[key] = value
                else:
                    unknown_updates[key] = value

            # Handle unknown keys (put them into 'attributes' and warn)
            if unknown_updates:
                warnings.warn(
                    f"The following metadata keys are not supported fields and will be "
                    f"added to 'attributes': {list(unknown_updates.keys())}"
                )

                # specific logic to merge with existing attributes safely
                current_attributes = dataset.metadata.attributes or {}
                # Create a new dict to avoid mutating the original if it's shared
                new_attributes = current_attributes.copy()
                new_attributes.update(unknown_updates)

                known_updates["attributes"] = new_attributes

            #  Apply updates
            if known_updates:
                updated_metadata = replace(dataset.metadata, **known_updates)
                dataset = replace(dataset, metadata=updated_metadata)

        # Check if we need to return a FilteredEventDataset
        if self.event_types:
            return dataset.filter(self.should_include_event)

        return dataset
