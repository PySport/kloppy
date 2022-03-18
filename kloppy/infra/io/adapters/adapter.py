from abc import abstractmethod, ABC
from typing import BinaryIO


class Adapter(ABC):
    @abstractmethod
    def supports(self, url: str) -> bool:
        pass

    @abstractmethod
    def read_to_stream(self, url: str, output: BinaryIO):
        pass


__all__ = ["Adapter"]
