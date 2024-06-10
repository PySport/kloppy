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
    Team,
    SubstitutionEvent,
    Position,
    Period,
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

    def _update_player_positions(
        self, teams: List[Team], events: List[Event], periods: List[Period]
    ):
        for event in events:
            if isinstance(event, SubstitutionEvent):
                event: SubstitutionEvent

                event.player.set_position(event.time, None)

                event.replacement_player.set_position(
                    event.time, Position.unknown()
                )

        # Set all player positions to None at end of match
        end_of_match = periods[-1].end_time
        for team in teams:
            for player in team.players:
                try:
                    if player.positions.value_at(end_of_match) is not None:
                        player.positions.set(end_of_match, None)
                except KeyError:
                    # Was not in the pitch
                    pass

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, inputs: T) -> EventDataset:
        raise NotImplementedError
