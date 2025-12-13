from abc import ABC, abstractmethod
from typing import BinaryIO, List

from kloppy.infra.io.buffered_stream import BufferedStream


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
    def read_to_stream(self, url: str, output: BufferedStream):
        pass

    def write_from_stream(self, url: str, input: BufferedStream, mode: str):
        """
        Write content from BufferedStream to the given URL.

        Args:
            url: The destination URL
            input: BufferedStream to read from
            mode: Write mode ('wb' for write/overwrite or 'ab' for append)

        Raises:
            NotImplementedError: If write operations are not supported by this adapter
        """
        raise NotImplementedError(
            f"Write operations not supported for {url}. "
            f"Adapter {self.__class__.__name__} does not implement write_from_stream."
        )

    @abstractmethod
    def list_directory(self, url: str, recursive: bool = True) -> List[str]:
        pass


__all__ = ["Adapter"]
