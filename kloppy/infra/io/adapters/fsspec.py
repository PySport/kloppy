import re
from abc import ABC, abstractmethod
from typing import BinaryIO, List, Optional

import fsspec

from kloppy.config import get_config
from kloppy.exceptions import InputNotFoundError

from .adapter import Adapter


class FSSpecAdapter(Adapter, ABC):
    def _infer_protocol(self, url: str) -> str:
        """
        Infer the protocol based on the URL prefix.
        """
        protocol_pattern = re.compile(r"^[a-zA-Z\d]+://")
        match = protocol_pattern.match(url)
        if match:
            return match.group(0)[
                :-3
            ]  # Remove '://' from the matched protocol
        return "file"  # Default to 'file' for local paths

    def _get_filesystem(
        self, url: str, no_cache: bool = False
    ) -> fsspec.AbstractFileSystem:
        """
        Get the appropriate fsspec filesystem for the given URL, with caching enabled.
        """
        protocol = self._infer_protocol(url)

        if no_cache:
            return fsspec.filesystem(protocol)

        return fsspec.filesystem(
            "simplecache",
            target_protocol=protocol,
            cache_storage=get_config("cache"),
        )

    def _detect_compression(self, url: str) -> Optional[str]:
        """
        Detect the compression type based on the file extension.
        Supported compression types include 'gzip', 'bz2', 'xz', etc.
        """
        compression_map = {
            ".gz": "gzip",
            ".bz2": "bz2",
            ".xz": "xz",
            ".zip": "zip",
        }
        for ext, comp in compression_map.items():
            if url.endswith(ext):
                return comp
        return None  # No compression detected

    @abstractmethod
    def supports(self, url: str) -> bool:
        """
        Check if the adapter can handle the URL.
        """

    def read_to_stream(self, url: str, output: BinaryIO):
        """
        Reads content from the given URL and writes it to the provided binary stream.
        Uses caching for remote files.
        """
        fs = self._get_filesystem(url)
        compression = self._detect_compression(url)

        try:
            with fs.open(url, "rb", compression=compression) as source_file:
                output.write(source_file.read())
        except FileNotFoundError as e:
            raise InputNotFoundError(f"Input file not found: {url}") from e

    def list_directory(self, url: str, recursive: bool = True) -> List[str]:
        """
        Lists the contents of a directory.
        """
        protocol = self._infer_protocol(url)
        fs = self._get_filesystem(url)
        if recursive:
            files = fs.find(url, detail=False)
        else:
            files = fs.listdir(url, detail=False)
        return [
            f"{protocol}://{fp}"
            if protocol != "file" and not fp.startswith(protocol)
            else fp
            for fp in files
        ]

    def is_directory(self, url: str) -> bool:
        """
        Check if the given URL points to a directory.
        """
        fs = self._get_filesystem(url)
        return fs.isdir(url)

    def is_file(self, url: str) -> bool:
        """
        Check if the given URL points to a file.
        """
        fs = self._get_filesystem(url)
        return fs.isfile(url)
