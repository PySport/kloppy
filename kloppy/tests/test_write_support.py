import bz2
import gzip
from io import BytesIO
import lzma
from pathlib import Path
from typing import BinaryIO

from kloppy.infra.io.adapters import Adapter
from kloppy.infra.io.buffered_stream import BufferedStream
from kloppy.io import open_as_file


class TestBufferedStream:
    """Tests for BufferedStream chunked copying."""

    def test_from_stream_small_data(self):
        """It should copy small data in chunks and keep in memory."""
        source = BytesIO(b"Small data content")
        buffer = BufferedStream.from_stream(source, chunk_size=8)

        assert buffer.read() == b"Small data content"
        assert buffer._rolled is False  # Still in memory

    def test_from_stream_large_data(self):
        """It should spill large data to disk."""
        buffer_size = 5 * 1024 * 1024  # 5MB
        large_data = b"x" * (buffer_size + 1000)
        source = BytesIO(large_data)
        buffer = BufferedStream.from_stream(source, max_size=buffer_size)

        assert buffer._rolled is True  # Spilled to disk
        assert buffer.read() == large_data


class MockWriteAdapter(Adapter):
    """Mock adapter for testing write support."""

    def __init__(self):
        self.written_data = {}

    def supports(self, url: str) -> bool:
        return url.startswith("mock://")

    def is_directory(self, url: str) -> bool:
        return False

    def is_file(self, url: str) -> bool:
        return url in self.written_data

    def read_to_stream(self, url: str, output: BinaryIO):
        if url in self.written_data:
            output.write(self.written_data[url])
        else:
            raise FileNotFoundError(f"Mock file not found: {url}")

    def write_from_stream(self, url: str, input: BinaryIO, mode: str):  # noqa: A002
        """Write data from input stream to mock storage."""
        input.seek(0)
        self.written_data[url] = input.read()

    def list_directory(self, url: str, recursive: bool = True) -> list[str]:
        return []


class TestOpenAsFileWrite:
    """Tests for write support in open_as_file."""

    def test_write_local_file(self, tmp_path: Path):
        """It should be able to write to a local file."""
        output_path = tmp_path / "output.txt"
        with open_as_file(output_path, mode="wb") as fp:
            assert fp is not None
            fp.write(b"Hello, write!")

        assert output_path.read_bytes() == b"Hello, write!"

    def test_write_compressed_gz(self, tmp_path: Path):
        """It should be able to write compressed gzip files."""
        output_path = tmp_path / "output.txt.gz"
        with open_as_file(output_path, mode="wb") as fp:
            assert fp is not None
            fp.write(b"Compressed content")

        # Verify by reading back
        with gzip.open(output_path, "rb") as f:
            assert f.read() == b"Compressed content"

    def test_write_compressed_bz2(self, tmp_path: Path):
        """It should be able to write compressed bz2 files."""
        output_path = tmp_path / "output.txt.bz2"
        with open_as_file(output_path, mode="wb") as fp:
            assert fp is not None
            fp.write(b"BZ2 content")

        with bz2.open(output_path, "rb") as f:
            assert f.read() == b"BZ2 content"

    def test_write_compressed_xz(self, tmp_path: Path):
        """It should be able to write compressed xz files."""
        output_path = tmp_path / "output.txt.xz"
        with open_as_file(output_path, mode="wb") as fp:
            assert fp is not None
            fp.write(b"XZ content")

        with lzma.open(output_path, "rb") as f:
            assert f.read() == b"XZ content"

    def test_write_bytesio(self):
        """It should be able to write to BytesIO."""
        buffer = BytesIO()
        with open_as_file(buffer, mode="wb") as fp:
            assert fp is not None
            fp.write(b"In-memory write")

        buffer.seek(0)
        assert buffer.read() == b"In-memory write"


class TestAdapterWrite:
    """Tests for adapter write support."""

    def test_write_via_adapter(self, monkeypatch):
        """It should use adapter's write_from_stream for remote writes."""
        from kloppy.infra.io import adapters

        mock_adapter = MockWriteAdapter()
        # Inject our mock adapter
        original_adapters = adapters.adapters
        monkeypatch.setattr(
            adapters, "adapters", [mock_adapter] + original_adapters
        )

        # Write via adapter
        with open_as_file("mock://test/file.txt", mode="wb") as fp:
            fp.write(b"Adapter write test")

        # Verify data was written to mock storage
        assert (
            mock_adapter.written_data["mock://test/file.txt"]
            == b"Adapter write test"
        )

        # Verify we can read it back
        with open_as_file("mock://test/file.txt") as fp:
            assert fp.read() == b"Adapter write test"
