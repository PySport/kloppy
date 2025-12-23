from abc import ABC, abstractmethod
from typing import BinaryIO


class Adapter(ABC):
    @abstractmethod
    def supports(self, url: str) -> bool:
        pass

    @abstractmethod
    def is_directory(self, url: str) -> bool:
        pass

    @abstractmethod
    def is_file(self, url: str) -> bool:
        pass

    @abstractmethod
    def read_to_stream(self, url: str, output: BinaryIO):
        pass

    @abstractmethod
    def list_directory(self, url: str, recursive: bool = True) -> list[str]:
        pass


__all__ = ["Adapter"]
