import base64
import bz2
import gzip
from io import BytesIO
import json
import lzma
import os
from pathlib import Path
import sys
from typing import BinaryIO, Optional
import zipfile

from botocore.session import Session
from moto.moto_server.threaded_moto_server import ThreadedMotoServer
import pytest

from kloppy.config import config_context
from kloppy.exceptions import InputNotFoundError, KloppyError
from kloppy.infra.io import adapters
from kloppy.infra.io.adapters import Adapter
from kloppy.infra.io.buffered_stream import BufferedStream
from kloppy.io import expand_inputs, get_file_extension, open_as_file

# --- Shared Helpers ---


def create_test_files(base_path: Path, content: str = "Hello, world!"):
    """Helper to generate standard test files (plain and compressed)."""
    # Plain text
    (base_path / "testfile.txt").write_text(content)

    # Compressed formats
    compressors = {
        ".gz": gzip.open,
        ".xz": lzma.open,
        ".bz2": bz2.open,
    }

    for ext, opener in compressors.items():
        with opener(base_path / f"testfile.txt{ext}", "wb") as f:
            f.write(content.encode("utf-8"))


@pytest.fixture
def populated_dir(tmp_path: Path) -> Path:
    """Fixture that returns a directory populated with standard test files."""
    create_test_files(tmp_path)
    return tmp_path


# --- Core IO Unit Tests ---


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


class TestOpenAsFile:
    """Tests for core open_as_file read/write functionality."""

    @pytest.fixture(params=[True, False], ids=["with_adapters", "no_adapters"])
    def setup_adapters(self, request, monkeypatch):
        """
        Fixture that runs tests in two states:
        1. Default state (adapters enabled).
        2. Patched state (adapters list empty).
        """
        if not request.param:
            monkeypatch.setattr(adapters, "adapters", [])

    # --- Read Tests ---

    def test_read_bytes(self):
        """It should be able to open a bytes object as a file."""
        with open_as_file(b"Hello, world!") as fp:
            assert fp.read() == b"Hello, world!"

    def test_read_data_string(self):
        """It should be able to open a json/xml string as a file."""
        with open_as_file('{"msg": "Hello, world!"}') as fp:
            assert json.load(fp) == {"msg": "Hello, world!"}

    def test_read_stream(self):
        """It should be able to open a byte stream as a file."""
        data = b"Hello, world!"
        with open_as_file(BytesIO(data)) as fp:
            assert fp.read() == data

    @pytest.mark.parametrize(
        "compress_func",
        [gzip.compress, bz2.compress, lzma.compress],
        ids=["gzip", "bz2", "xz"],
    )
    def test_read_compressed_stream(self, compress_func):
        """It should be able to open a compressed byte stream as a file."""
        data = compress_func(b"Hello, world!")
        with open_as_file(BytesIO(data)) as fp:
            assert fp.read() == b"Hello, world!"

    @pytest.mark.parametrize(
        "path_type", [str, Path], ids=["str_path", "Path_obj"]
    )
    def test_read_local_file_paths(
        self, populated_dir, path_type, setup_adapters
    ):
        """It should be able to open a local file (with and without adapters)."""
        path = path_type(populated_dir / "testfile.txt")
        with open_as_file(path) as fp:
            assert fp.read() == b"Hello, world!"

    @pytest.mark.parametrize("ext", ["gz", "xz", "bz2"])
    def test_read_compressed_local_file(
        self, populated_dir, ext, setup_adapters
    ):
        """It should be able to open a compressed local file (with and without adapters)."""
        path = populated_dir / f"testfile.txt.{ext}"
        with open_as_file(path) as fp:
            assert fp.read() == b"Hello, world!"

    def test_read_missing_file(self, tmp_path):
        """It should raise an error if the file is not found."""
        with pytest.raises(InputNotFoundError):
            open_as_file(tmp_path / "missing.txt")

    def test_read_opened_file(self, populated_dir):
        """It should return the same file object if already opened."""
        path = populated_dir / "testfile.txt"
        with open_as_file(path.open("rb")) as fp:
            assert fp.read() == b"Hello, world!"

    # --- Write Tests ---

    def test_write_stream(self):
        """It should be able to write to a byte stream."""
        buffer = BytesIO()
        with open_as_file(buffer, mode="wb") as fp:
            fp.write(b"In-memory write")

        buffer.seek(0)
        assert buffer.read() == b"In-memory write"

    @pytest.mark.parametrize(
        "path_type", [str, Path], ids=["str_path", "Path_obj"]
    )
    def test_write_local_file(self, tmp_path, path_type, setup_adapters):
        """It should be able to write to a local file (with and without adapters)."""
        output_path = path_type(tmp_path / "output.txt")
        with open_as_file(output_path, mode="wb") as fp:
            fp.write(b"Hello, write!")

        assert (tmp_path / "output.txt").read_bytes() == b"Hello, write!"

    @pytest.mark.parametrize(
        "ext, opener",
        [("gz", gzip.open), ("bz2", bz2.open), ("xz", lzma.open)],
        ids=["gzip", "bz2", "xz"],
    )
    def test_write_compressed_file(self, tmp_path, ext, opener, setup_adapters):
        """It should be able to write compressed files (with and without adapters)."""
        output_path = tmp_path / f"output.txt.{ext}"
        content = b"Compressed content"

        with open_as_file(output_path, mode="wb") as fp:
            fp.write(content)

        # Verify by reading back
        with opener(output_path, "rb") as f:
            assert f.read() == content

    def test_write_opened_file(self, tmp_path):
        """It should write to the same file object if already opened."""
        output_path = tmp_path / "output.txt"
        output_file = output_path.open("wb")
        with open_as_file(output_file, mode="wb") as fp:
            fp.write(b"Hello, opened write!")
        output_file.close()

        assert output_path.read_bytes() == b"Hello, opened write!"

    def test_mode_conflict(self, populated_dir):
        """It should raise an error if mode conflicts with opened file."""
        path = populated_dir / "testfile.txt"
        with pytest.raises(ValueError):
            open_as_file(path.open("r"), mode="wb")
        with pytest.raises(ValueError):
            open_as_file(path.open("wb"), mode="rb")
        with pytest.raises(ValueError):
            open_as_file(path.open("rb"), mode="wb")


class TestExpandInputs:
    @pytest.fixture
    def mock_fs(self, tmp_path):
        # Create a temporary directory structure
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.log").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").touch()

        # Return dict mapping keys to absolute string paths
        return {
            "root": os.fspath(tmp_path),
            "file1": os.fspath(tmp_path / "file1.txt"),
            "file2": os.fspath(tmp_path / "file2.log"),
            "file3": os.fspath(tmp_path / "subdir" / "file3.txt"),
        }

    def test_single_file(self, mock_fs):
        assert list(expand_inputs(mock_fs["file1"])) == [mock_fs["file1"]]

    def test_directory_expansion(self, mock_fs):
        expected = sorted(
            [mock_fs["file1"], mock_fs["file2"], mock_fs["file3"]]
        )
        assert sorted(expand_inputs(mock_fs["root"])) == expected

    def test_regex_filter(self, mock_fs):
        expected = sorted([mock_fs["file1"], mock_fs["file3"]])
        files = list(expand_inputs(mock_fs["root"], regex_filter=r".*.txt$"))
        assert sorted(files) == expected

    def test_sort_key(self, mock_fs):
        expected = sorted(
            [mock_fs["file1"], mock_fs["file2"], mock_fs["file3"]],
            key=lambda x: x[::-1],
        )
        files = list(expand_inputs(mock_fs["root"], sort_key=lambda x: x[::-1]))
        assert files == expected

    def test_list_of_files(self, mock_fs):
        inputs = [mock_fs["file1"], mock_fs["file2"]]
        assert list(expand_inputs(inputs)) == inputs

    def test_invalid_path(self):
        with pytest.raises(InputNotFoundError):
            list(expand_inputs("nonexistent.txt"))


def test_get_file_extension():
    assert get_file_extension(Path("data.xml")) == ".xml"
    assert get_file_extension("data.xml") == ".xml"
    assert get_file_extension("data.xml.gz") == ".xml"
    assert get_file_extension("data") == ""


# --- Adapter Integration Tests ---


class MockAdapter(Adapter):
    """
    Generic Mock adapter storing data in memory.
    Supports both read and write testing.
    """

    def __init__(self, initial_data: Optional[dict[str, bytes]] = None):
        self.storage = initial_data if initial_data else {}

    def supports(self, url: str) -> bool:
        return url.startswith("mock://")

    def is_directory(self, url: str) -> bool:
        return url not in self.storage and url.endswith("/")

    def is_file(self, url: str) -> bool:
        return url in self.storage

    def read_to_stream(self, url: str, output: BinaryIO):
        if url in self.storage:
            output.write(self.storage[url])
        else:
            raise FileNotFoundError(f"Mock file not found: {url}")

    def write_from_stream(self, url: str, input: BinaryIO, mode: str):  # noqa: A002
        input.seek(0)
        self.storage[url] = input.read()

    def list_directory(self, url: str, recursive: bool = True) -> list[str]:
        return [k for k in self.storage.keys() if k.startswith(url)]


class TestMockAdapter:
    """Tests for generic Adapter logic using the in-memory MockAdapter."""

    @pytest.fixture
    def adapter_setup(self, monkeypatch):
        # Pre-seed some data
        mock_adapter = MockAdapter(
            {
                "mock://read/data.txt": b"Pre-existing content",
                "mock://read/config.json": b'{"foo": "bar"}',
            }
        )

        # Inject adapter
        from kloppy.infra.io import adapters

        monkeypatch.setattr(
            adapters, "adapters", [mock_adapter] + adapters.adapters
        )
        return mock_adapter

    def test_expand_inputs(self, adapter_setup):
        expected = {"mock://read/data.txt", "mock://read/config.json"}
        assert set(expand_inputs("mock://read/")) == expected

    def test_read_via_adapter(self, adapter_setup):
        with open_as_file("mock://read/data.txt") as fp:
            assert fp.read() == b"Pre-existing content"

    def test_write_via_adapter(self, adapter_setup):
        with open_as_file("mock://write/new.txt", mode="wb") as fp:
            fp.write(b"New data")

        # Verify directly in storage
        assert adapter_setup.storage["mock://write/new.txt"] == b"New data"

        # Verify via read
        with open_as_file("mock://write/new.txt") as fp:
            assert fp.read() == b"New data"


class TestFileAdapter:
    """Tests for FileAdapter."""

    @pytest.fixture(autouse=True)
    def setup_files(self, populated_dir):
        self.root_dir = populated_dir

    def test_expand_inputs(self):
        """It should be able to list the contents of a local directory."""
        found = set(expand_inputs(str(self.root_dir)))
        assert found == {
            str(self.root_dir / f)
            for f in [
                "testfile.txt",
                "testfile.txt.gz",
                "testfile.txt.bz2",
                "testfile.txt.xz",
            ]
        }

    def test_read_via_adapter(self):
        """It should be able to open a file from the local filesystem."""
        path = self.root_dir / "testfile.txt"
        with open_as_file(str(path)) as fp:
            assert fp.read() == b"Hello, world!"

    def test_read_compressed_via_adapter(self):
        """It should be able to open and decompress a file from the local filesystem."""
        path = self.root_dir / "testfile.txt.gz"
        with open_as_file(str(path)) as fp:
            assert fp.read() == b"Hello, world!"

    def test_write_via_adapter(self):
        """It should be able to write a file to the local filesystem."""
        path = self.root_dir / "new_file.txt"
        with open_as_file(str(path), mode="wb") as fp:
            fp.write(b"New written data")

        assert path.exists()
        with open(path, "rb") as f:
            assert f.read() == b"New written data"

    def test_write_compressed_via_adapter(self):
        """It should be able to write a compressed file to the local filesystem."""
        path = self.root_dir / "new_file.txt.gz"
        with open_as_file(str(path), mode="wb") as fp:
            fp.write(b"New compressed data")

        assert path.exists()
        with gzip.open(path, "rb") as f:
            assert f.read() == b"New compressed data"


class TestHTTPAdapter:
    """Tests for HTTPAdapter."""

    @pytest.fixture(autouse=True)
    def httpserver_content(self, httpserver, tmp_path):
        """Set up the content to be read from an HTTP server."""
        # 1. Generate standard files
        create_test_files(tmp_path)

        # 2. Read binaries to serve
        txt_content = (tmp_path / "testfile.txt").read_bytes()
        gz_content = (tmp_path / "testfile.txt.gz").read_bytes()

        # 3. Configure Server
        httpserver.expect_request("/testfile.txt").respond_with_data(
            txt_content
        )

        # Serve compressed content with explicit headers
        httpserver.expect_request("/compressed_endpoint").respond_with_data(
            gz_content,
            headers={"Content-Encoding": "gzip", "Content-Type": "text/plain"},
        )

        # Serve generic .gz file
        httpserver.expect_request("/testfile.txt.gz").respond_with_data(
            gz_content, headers={"Content-Type": "application/x-gzip"}
        )

        # Serve protected file with basic auth
        encoded = base64.b64encode(b"Aladdin:OpenSesame").decode("utf-8")
        httpserver.expect_request(
            "/auth.txt", headers={"Authorization": f"Basic {encoded}"}
        ).respond_with_data(txt_content)
        httpserver.expect_request("/auth.txt").respond_with_data(
            "Unauthorized", status=401
        )

        index = f"""<html><body><ul>
            <li><a href="/testfile.txt">Txt</a></li>
            <li><a href="/compressed_endpoint">Comp</a></li>
            <li><a href="{httpserver.url_for("/testfile.txt.gz")}">Gz</a></li>
            <li><a href="/auth.txt">Auth</a></li>
        </ul></body></html>"""

        httpserver.expect_request("/").respond_with_data(
            index, headers={"Content-Type": "text/html"}
        )

        # make sure cache is reset for each test
        with config_context("cache", str(tmp_path / "http_cache")):
            yield httpserver

    def test_expand_inputs(self, httpserver):
        """It should be able to list the contents of an HTTP server."""
        url = httpserver.url_for("/")
        expected = {
            httpserver.url_for("/testfile.txt"),
            httpserver.url_for("/compressed_endpoint"),
            httpserver.url_for("/testfile.txt.gz"),
            httpserver.url_for("/auth.txt"),
        }
        assert set(expand_inputs(url)) == expected

    def test_read_via_adapter(self, httpserver):
        """It should be able to open a file from a URL."""
        with open_as_file(httpserver.url_for("/testfile.txt")) as fp:
            assert fp.read() == b"Hello, world!"

    def test_read_compressed_auto_decompress(self, httpserver):
        """It should decompress files based on Content-Encoding header."""
        with open_as_file(httpserver.url_for("/compressed_endpoint")) as fp:
            assert fp.read() == b"Hello, world!"

    def test_read_compressed_extension_handling(self, httpserver):
        """It should decompress files based on file extension."""
        with open_as_file(httpserver.url_for("/testfile.txt.gz")) as fp:
            assert fp.read() == b"Hello, world!"

    def test_write_unsupported(self, httpserver):
        """Writing data via the HTTP server is not supported."""
        with pytest.raises(NotImplementedError):
            with open_as_file(httpserver.url_for("/new.txt"), mode="wb") as fp:
                fp.write(b"Fail")

    def test_read_with_basic_auth(self, httpserver):
        """It should read a file protected with basic authentication."""
        # It should support a dict
        with config_context(
            "adapters.http.basic_authentication",
            {"login": "Aladdin", "password": "OpenSesame"},
        ):
            with open_as_file(httpserver.url_for("/auth.txt")) as fp:
                assert fp.read() == b"Hello, world!"

        # It should also support a tuple
        with config_context(
            "adapters.http.basic_authentication",
            ("Aladdin", "OpenSesame"),
        ):
            with open_as_file(httpserver.url_for("/auth.txt")) as fp:
                assert fp.read() == b"Hello, world!"

    def test_read_with_basic_auth_wrong_credentials(self, httpserver):
        """It should raise an error with incorrect basic authentication."""
        from aiohttp.client_exceptions import ClientResponseError

        with config_context(
            "adapters.http.basic_authentication",
            {"login": "Aladdin", "password": "CloseSesame"},
        ):
            with pytest.raises(ClientResponseError):
                with open_as_file(httpserver.url_for("/auth.txt")) as fp:
                    fp.read()

    def test_read_with_basic_auth_wrong_config(self, httpserver):
        """It should raise an error with malformed basic authentication config."""
        with config_context(
            "adapters.http.basic_authentication",
            {"user": "Aladdin", "pass": "OpenSesame"},  # Wrong keys
        ):
            with pytest.raises(
                KloppyError, match="Invalid basic authentication configuration"
            ):
                open_as_file(httpserver.url_for("/auth.txt"))


class TestZipAdapter:
    """Tests for ZipAdapter."""

    @pytest.fixture(autouse=True)
    def zip_config(self, tmp_path):
        """Creates a zip and sets it as the default zip adapter target."""
        zip_path = tmp_path / "archive.zip"
        create_test_files(tmp_path)

        # Create a zip containing two files
        with zipfile.ZipFile(zip_path, "w") as z:
            z.write(tmp_path / "testfile.txt", arcname="testfile.txt")
            z.write(tmp_path / "testfile.txt", arcname="other.txt")

        # Set config for test
        with config_context("adapters.zip.fo", str(zip_path)):
            yield

    def test_expand_inputs(self):
        """It should be able to list the contents of a zip archive."""
        expected = ["zip://other.txt", "zip://testfile.txt"]
        assert sorted(expand_inputs("zip:///")) == expected

    def test_read_via_adapter(self):
        """It should be able to open a file from a zip archive."""
        with open_as_file("zip://testfile.txt") as fp:
            assert fp.read() == b"Hello, world!"

    def test_write_via_adapter(self):
        """It should be able to add a file to a zip archive."""
        with open_as_file("zip://new_file.txt", mode="wb") as fp:
            fp.write(b"New written data")

        with open_as_file("zip://new_file.txt") as fp:
            assert fp.read() == b"New written data"


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="Patch requires Python 3.9 or higher"
)
class TestS3Adapter:
    """Tests for S3Adapter using moto."""

    endpoint_uri = "http://127.0.0.1:5555"
    bucket = "test-bucket"

    @pytest.fixture(scope="class", autouse=True)
    def s3_env(self, tmp_path_factory):
        # 1. Setup Moto Server
        server = ThreadedMotoServer(ip_address="127.0.0.1", port=5555)
        server.start()

        # 2. Setup Env
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "foo")
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "foo")

        # 3. Create generic test files locally first
        local_dir = tmp_path_factory.mktemp("s3_data")
        create_test_files(local_dir)

        # 4. Upload to Mock S3
        session = Session()
        client = session.create_client(
            "s3", endpoint_url=self.endpoint_uri, region_name="us-east-1"
        )
        client.create_bucket(Bucket=self.bucket, ACL="public-read")

        for file_path in local_dir.iterdir():
            client.put_object(
                Bucket=self.bucket,
                Key=file_path.name,
                Body=file_path.read_bytes(),
            )

        yield
        server.stop()

    @pytest.fixture(scope="class", autouse=True)
    def configure_kloppy_s3(self):
        from s3fs import S3FileSystem

        s3 = S3FileSystem(
            anon=False, client_kwargs={"endpoint_url": self.endpoint_uri}
        )
        with config_context("adapters.s3.s3fs", s3):
            yield

    def test_expand_inputs(self):
        """It should be able to list the contents of an S3 bucket."""
        found = set(expand_inputs(f"s3://{self.bucket}/"))
        assert found == {
            f"s3://{self.bucket}/{f}"
            for f in [
                "testfile.txt",
                "testfile.txt.gz",
                "testfile.txt.bz2",
                "testfile.txt.xz",
            ]
        }

    def test_read_via_adapter(self):
        """It should be able to open a file from an S3 bucket."""
        with open_as_file(f"s3://{self.bucket}/testfile.txt") as fp:
            assert fp.read() == b"Hello, world!"

    def test_read_compressed_via_adapter(self):
        """It should be able to open a compressed file from an S3 bucket."""
        with open_as_file(f"s3://{self.bucket}/testfile.txt.gz") as fp:
            assert fp.read() == b"Hello, world!"

    def test_write_via_adapter(self):
        """It should be able to write a file to an S3 bucket."""
        path = f"s3://{self.bucket}/new_s3_file.txt"
        with open_as_file(path, mode="wb") as fp:
            fp.write(b"New data")

        with open_as_file(path) as fp:
            assert fp.read() == b"New data"
