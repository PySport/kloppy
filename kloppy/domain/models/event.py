# Metrica Documentation https://github.com/metrica-sports/sample-data/blob/master/documentation/events-definitions.pdf
from abc import ABC, abstractmethod, abstractproperty, ABCMeta
from dataclasses import dataclass
from enum import Enum
from typing import List, Union

from .pitch import Point
from .common import DataRecord, DataSet, Team


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


class DribbleCarryResult(ResultType):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    OUT = "OUT"

    @property
    def is_success(self):
        return self == self.COMPLETE


class EventType(Enum):
    PASS = "PASS"
    SHOT = "SHOT"
    DRIBBLE = "DRIBBLE"
    CARRY = "CARRY"


@dataclass
class Event(DataRecord, ABC):
    event_id: str
    team: Team

    player_jersey_no: str
    position: Point

    result: ResultType

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        raise NotImplementedError


@dataclass
class ShotEvent(Event):
    result: ShotResult

    event_type: EventType = EventType.SHOT


@dataclass
class PassEvent(Event):
    end_timestamp: float
    receiver_player_jersey_no: str
    receiver_position: Point

    result: PassResult

    event_type: EventType = EventType.PASS


@dataclass
class DribbleEvent(Event):
    end_timestamp: float
    end_position: Point

    result: DribbleCarryResult

    event_type: EventType = EventType.DRIBBLE


@dataclass
class CarryEvent(Event):
    end_timestamp: float
    end_position: Point

    result: DribbleCarryResult

    event_type: EventType = EventType.CARRY


@dataclass
class EventDataSet(DataSet):
    records: List[Union[
        ShotEvent, PassEvent, DribbleEvent, CarryEvent
    ]]

    @property
    def events(self):
        return self.records


__all__ = [
    "ResultType", "EventType",
    "ShotResult", "PassResult", "DribbleCarryResult",
    "ShotEvent", "PassEvent", "DribbleEvent", "CarryEvent",
    "EventDataSet"
]
