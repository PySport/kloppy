import gzip
import json
from io import BytesIO
from pathlib import Path

import pytest
import s3fs
from moto import mock_aws

from kloppy.exceptions import InputNotFoundError
from kloppy.io import get_file_extension, open_as_file


@pytest.fixture()
def filesystem_content(tmp_path: Path):
    """Set up the content to be read from a file."""
    path = tmp_path / "testfile.txt"
    with open(path, "w") as f:
        f.write("Hello, world!")

    gz_path = tmp_path / "testfile.txt.gz"
    with open(gz_path, "wb") as f:
        import gzip

        with gzip.open(f, "wb") as f_out:
            f_out.write(b"Hello, world!")

    xz_path = tmp_path / "testfile.txt.xz"
    with open(xz_path, "wb") as f:
        import lzma

        with lzma.open(f, "wb") as f_out:
            f_out.write(b"Hello, world!")

    bz2_path = tmp_path / "testfile.txt.bz2"
    with open(bz2_path, "wb") as f:
        import bz2

        with bz2.open(f, "wb") as f_out:
            f_out.write(b"Hello, world!")

    return tmp_path


@pytest.fixture
def httpserver_content(httpserver):
    """Set up the content to be read from a HTTP server."""
    httpserver.expect_request("/testfile.txt").respond_with_data(
        "Hello, world!"
    )
    httpserver.expect_request("/compressed_testfile.txt").respond_with_data(
        gzip.compress(b"Hello, world!"),
        headers={"Content-Encoding": "gzip", "Content-Type": "text/plain"},
    )
    httpserver.expect_request("/testfile.txt.gz").respond_with_data(
        gzip.compress(b"Hello, world!"),
        headers={"Content-Type": "application/x-gzip"},
    )


@pytest.fixture
def s3_content():
    with mock_aws():
        s3_fs = s3fs.S3FileSystem(anon=True)
        s3_fs.mkdir("test-bucket", region_name="eu-central-1")
        with s3_fs.open("test-bucket/testfile.txt", "wb") as f:
            f.write(b"Hello, world!")
        with s3_fs.open("test-bucket/testfile.txt.gz", "wb") as f:
            f.write(gzip.compress(b"Hello, world!"))
        yield s3_fs
        s3_fs.rm("test-bucket", recursive=True)


class TestOpenAsFile:
    """Tests for the open_as_file function."""

    def test_bytes(self):
        """It should be able to open a file from a bytes object."""
        with open_as_file(b"Hello, world!") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_data_string(self):
        """It should be able to open a file from a string object."""
        with open_as_file('{"msg": "Hello, world!"}') as fp:
            assert fp is not None
            assert json.load(fp) == {"msg": "Hello, world!"}

    def test_stream(self):
        """It should be able to open a file from a byte stream object."""
        data = b"Hello, world!"
        with open_as_file(BytesIO(data)) as fp:
            assert fp is not None
            assert fp.read() == data

    def test_path_str(self, filesystem_content: Path):
        """It should be able to open a file from a string path."""
        path = str(filesystem_content / "testfile.txt")
        with open_as_file(path) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_path_obj(self, filesystem_content: Path):
        """It should be able to open a file from a Path object."""
        path = filesystem_content / "testfile.txt"
        with open_as_file(path) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    @pytest.mark.parametrize("ext", [".gz", ".xz", ".bz2"])
    def test_path_compressed(self, filesystem_content: Path, ext: str):
        """It should be able to open a compressed local file."""
        path = filesystem_content / f"testfile.txt{ext}"
        with open_as_file(path) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_path_missing(self, filesystem_content: Path):
        """It should raise an error if the file is not found."""
        path = filesystem_content / "missing.txt"
        with pytest.raises(InputNotFoundError):
            with open_as_file(path) as fp:
                pass

    def test_http(self, httpserver, httpserver_content):
        """It should be able to open a file from a URL."""
        url = httpserver.url_for("/testfile.txt")
        with open_as_file(url) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_http_compressed(self, httpserver, httpserver_content):
        """It should be able to open a compressed file from a URL."""
        # If the server returns a content-encoding header, the file should be
        # decompressed by the request library
        url = httpserver.url_for("/compressed_testfile.txt")
        with open_as_file(url) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

        # If the server does not set a content-type header, but the URL ends
        # with .gz, the file should be decompressed by kloppy
        url = httpserver.url_for("/testfile.txt.gz")
        with open_as_file(url) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    @pytest.mark.skip(
        reason="see https://github.com/aio-libs/aiobotocore/issues/755"
    )
    def test_s3(self, s3_content):
        """It should be able to open a file from an S3 bucket."""
        with open_as_file("s3://test-bucket/testfile.txt") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    @pytest.mark.skip(
        reason="see https://github.com/aio-libs/aiobotocore/issues/755"
    )
    def test_s3_compressed(self, s3_content):
        """It should be able to open a file from an S3 bucket."""
        with open_as_file("s3://test-bucket/testfile.txt.gz") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"


def test_get_file_extension():
    assert get_file_extension(Path("data.xml")) == ".xml"
    assert get_file_extension("data.xml") == ".xml"
    assert get_file_extension("data.xml.gz") == ".xml"
    assert get_file_extension("data") == ""
