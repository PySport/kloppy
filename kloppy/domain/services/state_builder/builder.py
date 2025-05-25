from abc import abstractmethod
from typing import TypeVar

from kloppy.domain import Event, EventDataset

from .registered import RegisteredStateBuilder

T = TypeVar("T")


class StateBuilder(metaclass=RegisteredStateBuilder):
    @abstractmethod
    def initial_state(self, dataset: EventDataset) -> T:
        pass

    @abstractmethod
    def reduce_before(self, state: T, event: Event) -> T:
        pass

    @abstractmethod
    def reduce_after(self, state: T, event: Event) -> T:
        pass
