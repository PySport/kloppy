from abc import abstractmethod, ABC
from typing import TypeVar

from kloppy.domain import EventDataset, Event

T = TypeVar("T")


class StateBuilder(ABC):
    @abstractmethod
    def initial_state(self, dataset: EventDataset) -> T:
        pass

    @abstractmethod
    def reduce(self, state: T, event: Event) -> T:
        pass
