# Metrica Documentation https://github.com/metrica-sports/sample-data/blob/master/documentation/events-definitions.pdf
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Union, Dict

from kloppy.domain.models.common import DatasetType

from .common import DataRecord, Dataset, Team, Player
from .pitch import Point


class ResultType(Enum):
    @property
    @abstractmethod
    def is_success(self):
        raise NotImplementedError


class ShotResult(ResultType):
    GOAL = "GOAL"
    OFF_TARGET = "OFF_TARGET"
    POST = "POST"
    BLOCKED = "BLOCKED"
    SAVED = "SAVED"

    @property
    def is_success(self):
        return self == self.GOAL


class PassResult(ResultType):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    OUT = "OUT"
    OFFSIDE = "OFFSIDE"

    @property
    def is_success(self):
        return self == self.COMPLETE


class TakeOnResult(ResultType):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    OUT = "OUT"

    @property
    def is_success(self):
        return self == self.COMPLETE


class CarryResult(ResultType):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"

    @property
    def is_success(self):
        return self == self.COMPLETE


class CardType(Enum):
    FIRST_YELLOW = "FIRST_YELLOW"
    SECOND_YELLOW = "SECOND_YELLOW"
    RED = "RED"


class EventType(Enum):
    GENERIC = "generic"

    PASS = "PASS"
    SHOT = "SHOT"
    TAKE_ON = "TAKE_ON"
    CARRY = "CARRY"
    SUBSTITUTION = "SUBSTITUTION"
    CARD = "CARD"
    PLAYER_ON = "PLAYER_ON"
    PLAYER_OFF = "PLAYER_OFF"


@dataclass
class Event(DataRecord, ABC):
    event_id: str
    team: Team
    player: Player
    coordinates: Point

    result: Union[ResultType, None]

    raw_event: Dict
    state: Dict[str, any]

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        raise NotImplementedError

    @property
    @abstractmethod
    def event_name(self) -> str:
        raise NotImplementedError

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs, state={})


@dataclass
class GenericEvent(Event):
    event_name: str = "generic"
    event_type: EventType = EventType.GENERIC


@dataclass
class ShotEvent(Event):
    result: ShotResult

    event_type: EventType = EventType.SHOT
    event_name: str = "shot"


@dataclass
class PassEvent(Event):
    receive_timestamp: float
    receiver_player: Player
    receiver_coordinates: Point

    result: PassResult

    event_type: EventType = EventType.PASS
    event_name: str = "pass"


@dataclass
class TakeOnEvent(Event):
    result: TakeOnResult

    event_type: EventType = EventType.TAKE_ON
    event_name: str = "take-on"


@dataclass
class CarryEvent(Event):
    end_timestamp: float
    end_coordinates: Point

    result: CarryResult

    event_type: EventType = EventType.CARRY
    event_name: str = "carry"


@dataclass
class SubstitutionEvent(Event):
    replacement_player: Player

    event_type: EventType = EventType.SUBSTITUTION
    event_name: str = "substitution"


@dataclass
class PlayerOffEvent(Event):
    event_type: EventType = EventType.PLAYER_OFF
    event_name: str = "player_off"


@dataclass
class PlayerOnEvent(Event):
    event_type: EventType = EventType.PLAYER_ON
    event_name: str = "player_on"


@dataclass
class CardEvent(Event):
    card_type: CardType

    event_type: EventType = EventType.CARD
    event_name: str = "card"


@dataclass
class EventDataset(Dataset):
    records: List[
        Union[
            GenericEvent,
            ShotEvent,
            PassEvent,
            TakeOnEvent,
            CarryEvent,
            SubstitutionEvent,
            PlayerOffEvent,
            PlayerOnEvent,
            CardEvent,
        ]
    ]

    dataset_type: DatasetType = DatasetType.EVENT

    @property
    def events(self):
        return self.records

    def add_state(self, *args, **kwargs):
        from kloppy import add_state

        return add_state(self, *args, **kwargs)


__all__ = [
    "ResultType",
    "EventType",
    "ShotResult",
    "PassResult",
    "TakeOnResult",
    "CarryResult",
    "Event",
    "GenericEvent",
    "ShotEvent",
    "PassEvent",
    "TakeOnEvent",
    "CarryEvent",
    "SubstitutionEvent",
    "PlayerOnEvent",
    "PlayerOffEvent",
    "CardEvent",
    "CardType",
    "EventDataset",
]
