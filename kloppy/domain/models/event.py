# Metrica Documentation https://github.com/metrica-sports/sample-data/blob/master/documentation/events-definitions.pdf
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Type, Union

from kloppy.domain.models.common import DatasetType
from kloppy.utils import camelcase_to_snakecase, removes_suffix

from .common import DataRecord, Dataset, Player, Team
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
    RECOVERY = "RECOVERY"
    BALL_OUT = "BALL_OUT"
    FOUL_COMMITTED = "FOUL_COMMITTED"


@dataclass
class Qualifier(ABC):
    value: None

    @abstractmethod
    def to_dict(self):
        pass

    @property
    def name(self):
        return camelcase_to_snakecase(
            removes_suffix(type(self).__name__, "Qualifier")
        )


@dataclass
class BoolQualifier(Qualifier, ABC):
    value: bool

    def to_dict(self):
        return {f"is_{self.name}": self.value}


class EnumQualifier(Qualifier, ABC):
    value: Enum

    def to_dict(self):
        return {f"{self.name}_type": self.value.value}


class SetPieceType(Enum):
    GOAL_KICK = "GOAL_KICK"
    FREE_KICK = "FREE_KICK"
    THROW_IN = "THROW_IN"
    CORNER_KICK = "CORNER_KICK"
    PENALTY = "PENALTY"
    KICK_OFF = "KICK_OFF"


@dataclass
class SetPieceQualifier(EnumQualifier):
    value: SetPieceType


class PassType(Enum):
    CROSS = "CROSS"
    HAND_PASS = "HAND_PASS"
    HEAD_PASS = "HEAD_PASS"
    HIGH_PASS = "HIGH_PASS"
    LAUNCH = "LAUNCH"
    SIMPLE_PASS = "SIMPLE_PASS"
    SMART_PASS = "SMART_PASS"


@dataclass
class PassQualifier(EnumQualifier):
    value: PassType


class BodyPart(Enum):
    RIGHT_FOOT = "RIGHT_FOOT"
    LEFT_FOOT = "LEFT_FOOT"
    HEAD = "HEAD"


@dataclass
class BodyPartQualifier(EnumQualifier):
    value: BodyPart


class GoalkeeperAction(Enum):
    REFLEX = "REFLEX"
    SAVE_ATTEMPT = "SAVE_ATTEMPT"


@dataclass
class GoalkeeperActionQualifier(EnumQualifier):
    value: GoalkeeperAction


@dataclass
class CounterAttackQualifier(BoolQualifier):
    pass


@dataclass
class Event(DataRecord, ABC):
    event_id: str
    team: Team
    player: Player
    coordinates: Point

    result: Union[ResultType, None]

    raw_event: Dict
    state: Dict[str, any]

    qualifiers: List[Qualifier]

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

    def get_qualifier_value(self, qualifier_type: Type[Qualifier]):
        if self.qualifiers:
            for qualifier in self.qualifiers:
                if isinstance(qualifier, qualifier_type):
                    return qualifier.value
        return None


@dataclass
class GenericEvent(Event):
    event_name: str = "generic"
    event_type: EventType = EventType.GENERIC


@dataclass
class ShotEvent(Event):
    result: ShotResult
    result_coordinates: Point = None

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
class RecoveryEvent(Event):
    event_type: EventType = EventType.RECOVERY
    event_name: str = "recovery"


@dataclass
class BallOutEvent(Event):
    event_type: EventType = EventType.BALL_OUT
    event_name: str = "ball_out"


@dataclass
class FoulCommittedEvent(Event):
    event_type: EventType = EventType.FOUL_COMMITTED
    event_name: str = "foul_committed"


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
    "RecoveryEvent",
    "FoulCommittedEvent",
    "BallOutEvent",
    "SetPieceType",
    "Qualifier",
    "SetPieceQualifier",
    "PassQualifier",
    "PassType",
    "BodyPart",
    "BodyPartQualifier",
    "GoalkeeperAction",
    "GoalkeeperActionQualifier",
    "CounterAttackQualifier",
]
