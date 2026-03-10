from abc import ABC, abstractmethod

from kloppy.infra.io.buffered_stream import BufferedStream


class Adapter(ABC):
    @abstractmethod
    def supports(self, url: str) -> bool:
        """Returns True if this adapter supports the given URL, False otherwise."""

    @abstractmethod
    def is_directory(self, url: str) -> bool:
        """Returns True if the given URL points to a directory, False otherwise."""

    @abstractmethod
    def is_file(self, url: str) -> bool:
        """Returns True if the given URL points to a file, False otherwise."""

    @abstractmethod
    def read_to_stream(self, url: str, output: BufferedStream):
        """Read content from the given URL into the BufferedStream.

        Args:
            url: The source URL
            output: BufferedStream to write to
        """

    def write_from_stream(self, url: str, input: BufferedStream, mode: str):  # noqa: A002
        """Write content from BufferedStream to the given URL.

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
    def list_directory(self, url: str, recursive: bool = True) -> list[str]:
        """Lists the contents of a directory.

        Args:
            url: The directory URL
            recursive: Whether to list contents recursively

        Returns:
            A list of files in the directory

        Example:
            >>> adapter.list_directory("s3://my-bucket/data/", recursive=False)
            ['s3://my-bucket/data/file1.csv', 's3://my-bucket/data/file2.csv']
        """


__all__ = ["Adapter"]
