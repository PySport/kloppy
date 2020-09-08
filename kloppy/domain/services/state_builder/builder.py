from abc import abstractmethod
from typing import TypeVar

from kloppy.domain import EventDataset, Event
from .registered import RegisteredStateBuilder

T = TypeVar("T")


class StateBuilder(metaclass=RegisteredStateBuilder):
    @abstractmethod
    def initial_state(self, dataset: EventDataset) -> T:
        pass

    @abstractmethod
    def reduce(self, state: T, event: Event) -> T:
        pass
