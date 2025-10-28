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
        exclude_penalty_shootouts: bool = False,
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
        self.exclude_penalty_shootouts = exclude_penalty_shootouts

    def should_include_event(self, event: Event) -> bool:
        if (
            self.exclude_penalty_shootouts
            and event.period
            and event.period.id == 5
        ):
            return False
        if not self.event_types:
            return True
        return event.event_type in self.event_types

    def remove_penalty_shootout_data(
        self, dataset: EventDataset
    ) -> EventDataset:
        """
        Remove all penalty shootout data from the dataset including:
        - Period 5 from metadata.periods
        - Player positions associated with period 5
        - Team formations associated with period 5
        """
        if not self.exclude_penalty_shootouts:
            return dataset

        # Remove period 5 from metadata.periods
        dataset.metadata.periods = [
            period for period in dataset.metadata.periods if period.id != 5
        ]

        # Update period references (prev/next) after removal
        for i, period in enumerate(dataset.metadata.periods):
            period.set_refs(
                prev=dataset.metadata.periods[i - 1] if i > 0 else None,
                next_=(
                    dataset.metadata.periods[i + 1]
                    if i + 1 < len(dataset.metadata.periods)
                    else None
                ),
            )

        # Remove player positions and team formations associated with period 5
        for team in dataset.metadata.teams:
            # Filter out formations for period 5
            if team.formations.items:
                times_to_remove = [
                    time
                    for time in team.formations.items.keys()
                    if time.period and time.period.id == 5
                ]
                for time in times_to_remove:
                    del team.formations.items[time]

            # Filter out player positions for period 5
            for player in team.players:
                if player.positions.items:
                    times_to_remove = [
                        time
                        for time in player.positions.items.keys()
                        if time.period and time.period.id == 5
                    ]
                    for time in times_to_remove:
                        del player.positions.items[time]

        return dataset

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
    def deserialize(self, inputs: T) -> EventDataset:
        raise NotImplementedError
