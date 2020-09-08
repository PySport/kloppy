from abc import abstractmethod, ABC
from typing import TypeVar, Generic

from kloppy.domain import EventDataset, Event
from .registered import RegisteredStateBuilder

T = TypeVar("T")


class StateBuilder(Generic[T], metaclass=RegisteredStateBuilder):
    @abstractmethod
    def initial_state(self, dataset: EventDataset) -> T:
        pass

    @abstractmethod
    def reduce(self, state: T, event: Event) -> T:
        pass
