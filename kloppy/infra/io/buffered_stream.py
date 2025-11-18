"""Buffered stream utilities for efficient I/O operations."""

import shutil
import tempfile
from typing import BinaryIO, Protocol

DEFAULT_BUFFER_SIZE = 5 * 1024 * 1024  # 5MB before spilling to disk


class SupportsWrite(Protocol):
    """Protocol for objects that support write operations."""

    def write(self, data: bytes) -> int:
        ...


class SupportsRead(Protocol):
    """Protocol for objects that support read operations."""

    def read(self, n: int) -> bytes:
        ...


class BufferedStream(tempfile.SpooledTemporaryFile):
    """A spooled temporary file that can efficiently copy from streams in chunks."""

    def __init__(self, max_size: int = DEFAULT_BUFFER_SIZE, mode: str = "w+b"):
        super().__init__(max_size=max_size, mode=mode)

    def write(self, data: bytes) -> int:  # make it clearly bytes-only
        return super().write(data)

    def read(self, n: int = -1) -> bytes:  # make it clearly bytes-only
        return super().read(n)

    @classmethod
    def from_stream(
        cls,
        source: BinaryIO,
        max_size: int = DEFAULT_BUFFER_SIZE,
        chunk_size: int = 0,
    ) -> "BufferedStream":
        """
        Create a BufferedStream by copying data from source stream in chunks.

        Args:
            source: The source binary stream to read from
            max_size: Maximum size to keep in memory before spilling to disk
            chunk_size: Size of chunks to keep in memory before spilling to disk

        Returns:
            A BufferedStream containing the copied data
        """
        buffer = cls(max_size=max_size)
        buffer.read_from(source, chunk_size)
        return buffer

    def read_from(self, source: SupportsRead, chunk_size: int = 0):
        """
        Read data from source into this BufferedStream in chunks.

        Args:
            source: The source that supports read() method
            chunk_size: Size of chunks to copy at a time (0 uses default)
        """
        shutil.copyfileobj(source, self, chunk_size)
        self.seek(0)

    def write_to(self, output: SupportsWrite, chunk_size: int = 0) -> None:
        """
        Write all contents of this BufferedStream to the output in chunks.

        Args:
            output: The destination that supports write() method
            chunk_size: Size of chunks to keep in memory before spilling to disk
        """
        self.seek(0)
        shutil.copyfileobj(self, output, chunk_size)
