import bz2
import gzip
import json
import lzma
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from botocore.session import Session
from moto.moto_server.threaded_moto_server import ThreadedMotoServer

from kloppy.config import set_config
from kloppy.exceptions import InputNotFoundError
from kloppy.io import expand_inputs, get_file_extension, open_as_file


@pytest.fixture()
def filesystem_content(tmp_path: Path) -> Path:
    """Set up the content to be read from a local filesystem."""
    content = "Hello, world!"
    content_bytes = content.encode("utf-8")

    # Create a regular text file
    text_file = tmp_path / "testfile.txt"
    text_file.write_text(content)

    # Create a gzip-compressed file
    gz_file = tmp_path / "testfile.txt.gz"
    with gzip.open(gz_file, "wb") as f_out:
        f_out.write(content_bytes)

    # Create a xz-compressed file
    xz_file = tmp_path / "testfile.txt.xz"
    with lzma.open(xz_file, "wb") as f_out:
        f_out.write(content_bytes)

    # Create a bzip2-compressed file
    bz2_file = tmp_path / "testfile.txt.bz2"
    with bz2.open(bz2_file, "wb") as f_out:
        f_out.write(content_bytes)

    return tmp_path


class TestOpenAsFile:
    """Tests for the open_as_file function."""

    def test_bytes(self):
        """It should be able to open a bytes object as a file."""
        with open_as_file(b"Hello, world!") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_data_string(self):
        """It should be able to open a json/xml string as a file."""
        with open_as_file('{"msg": "Hello, world!"}') as fp:
            assert fp is not None
            assert json.load(fp) == {"msg": "Hello, world!"}

    def test_stream(self):
        """It should be able to open a byte stream as a file."""
        data = b"Hello, world!"
        with open_as_file(BytesIO(data)) as fp:
            assert fp is not None
            assert fp.read() == data

    @pytest.mark.parametrize(
        "compress_func",
        [
            gzip.compress,
            bz2.compress,
            lzma.compress,
        ],
        ids=["gzip", "bz2", "xz"],
    )
    def test_compressed_stream(self, compress_func):
        """It should be able to open a compressed byte stream as a file."""
        data = compress_func(b"Hello, world!")
        with open_as_file(BytesIO(data)) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

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

    @pytest.mark.parametrize("ext", ["gz", "xz", "bz2"])
    def test_path_compressed(self, filesystem_content: Path, ext: str):
        """It should be able to open a compressed local file."""
        path = filesystem_content / f"testfile.txt.{ext}"
        with open_as_file(path) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_path_missing(self, filesystem_content: Path):
        """It should raise an error if the file is not found."""
        path = filesystem_content / "missing.txt"
        with pytest.raises(InputNotFoundError):
            with open_as_file(path) as _:
                pass


class TestExpandInputs:
    @pytest.fixture
    def mock_filesystem(self, tmp_path):
        # Create a temporary directory structure
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.log"
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file3 = subdir / "file3.txt"

        file1.write_text("Content of file1")
        file2.write_text("Content of file2")
        file3.write_text("Content of file3")

        return {
            "root": str(tmp_path.as_posix()),
            "file1": str(file1.as_posix()),
            "file2": str(file2.as_posix()),
            "subdir": str(subdir.as_posix()),
            "file3": str(file3.as_posix()),
        }

    def test_single_file(self, mock_filesystem):
        files = list(expand_inputs(mock_filesystem["file1"]))
        assert files == [mock_filesystem["file1"]]

    def test_directory_expansion(self, mock_filesystem):
        files = sorted(expand_inputs(mock_filesystem["root"]))
        expected_files = sorted(
            [
                mock_filesystem["file1"],
                mock_filesystem["file2"],
                mock_filesystem["file3"],
            ]
        )
        assert files == expected_files

    def test_regex_filter(self, mock_filesystem):
        files = list(
            expand_inputs(mock_filesystem["root"], regex_filter=r".*.txt$")
        )
        expected_files = [
            mock_filesystem["file1"],
            mock_filesystem["file3"],
        ]
        assert sorted(files) == sorted(expected_files)

    def test_sort_key(self, mock_filesystem):
        files = list(
            expand_inputs(mock_filesystem["root"], sort_key=lambda x: x[::-1])
        )
        expected_files = sorted(
            [
                mock_filesystem["file1"],
                mock_filesystem["file2"],
                mock_filesystem["file3"],
            ],
            key=lambda x: x[::-1],
        )
        assert files == expected_files

    def test_list_of_files(self, mock_filesystem):
        input_list = [mock_filesystem["file1"], mock_filesystem["file2"]]
        files = list(expand_inputs(input_list))
        assert files == input_list

    def test_invalid_path(self):
        with pytest.raises(InputNotFoundError):
            list(expand_inputs("nonexistent_file.txt"))


def test_get_file_extension():
    assert get_file_extension(Path("data.xml")) == ".xml"
    assert get_file_extension("data.xml") == ".xml"
    assert get_file_extension("data.xml.gz") == ".xml"
    assert get_file_extension("data") == ""


class TestHTTPAdapter:
    @pytest.fixture(autouse=True)
    def httpserver_content(self, httpserver):
        """Set up the content to be read from an HTTP server."""
        # Define the content
        content = "Hello, world!"
        compressed_content = gzip.compress(b"Hello, world!")

        # Serve the plain text file
        httpserver.expect_request("/testfile.txt").respond_with_data(content)

        # Serve the compressed text file with Content-Encoding header
        httpserver.expect_request(
            "/compressed_testfile.txt"
        ).respond_with_data(
            compressed_content,
            headers={"Content-Encoding": "gzip", "Content-Type": "text/plain"},
        )

        # Serve the gzip file with application/x-gzip content type
        httpserver.expect_request("/testfile.txt.gz").respond_with_data(
            compressed_content,
            headers={"Content-Type": "application/x-gzip"},
        )

        # Generate the index.html content with links to all resources
        index_html = f"""
        <html>
            <head><title>Test Content</title></head>
            <body>
                <h1>Available Data</h1>
                <ul>
                    <li><a href="/testfile.txt">Plain Text File</a></li>
                    <li><a href="/compressed_testfile.txt">Compressed Text File (gzip)</a></li>
                    <li><a href="{httpserver.url_for("/testfile.txt.gz")}">Gzip File</a></li>
                </ul>
            </body>
        </html>
        """

        # Serve the index.html page
        httpserver.expect_request("/").respond_with_data(
            index_html, headers={"Content-Type": "text/html"}
        )

        return httpserver

    def test_expand_inputs(self, httpserver):
        """It should be able to list the contents of an HTTP server."""
        url = httpserver.url_for("/")
        assert list(expand_inputs(url)) == [
            httpserver.url_for("/compressed_testfile.txt"),
            httpserver.url_for("/testfile.txt"),
            httpserver.url_for("/testfile.txt.gz"),
        ]

    def test_open_as_file(self, httpserver):
        """It should be able to open a file from a URL."""
        url = httpserver.url_for("/testfile.txt")
        with open_as_file(url) as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_open_as_file_compressed(self, httpserver):
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


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="Patch requires Python 3.9 or higher"
)
class TestS3Adapter:
    endpoint_uri = "http://127.0.0.1:5555"
    test_bucket_name = "test-bucket"
    files = {
        "testfile.txt": b"Hello, world!",
        "testfile.txt.gz": gzip.compress(b"Hello, world!"),
    }

    @pytest.fixture(scope="class", autouse=True)
    def s3_content(self):
        """Set up the content to be read from a S3 bucket."""
        server = ThreadedMotoServer(ip_address="127.0.0.1", port=5555)
        server.start()
        if "AWS_SECRET_ACCESS_KEY" not in os.environ:
            os.environ["AWS_SECRET_ACCESS_KEY"] = "foo"
        if "AWS_ACCESS_KEY_ID" not in os.environ:
            os.environ["AWS_ACCESS_KEY_ID"] = "foo"

        session = Session()
        client = session.create_client(
            "s3", endpoint_url=self.endpoint_uri, region_name="us-east-1"
        )
        client.create_bucket(Bucket=self.test_bucket_name, ACL="public-read")

        for f, data in self.files.items():
            client.put_object(Bucket=self.test_bucket_name, Key=f, Body=data)

        yield

        server.stop()

    @pytest.fixture(scope="class", autouse=True)
    def s3fs(self):
        """Set up the S3FileSystem."""
        from s3fs import S3FileSystem

        s3 = S3FileSystem(
            anon=False, client_kwargs={"endpoint_url": self.endpoint_uri}
        )
        set_config("adapters.s3.s3fs", s3)

    def test_list_directory(self):
        """It should be able to list the contents of an S3 bucket."""
        assert set(expand_inputs("s3://test-bucket/")) == {
            "s3://test-bucket/testfile.txt",
            "s3://test-bucket/testfile.txt.gz",
        }

    def test_open_as_file(self):
        """It should be able to open a file from an S3 bucket."""
        with open_as_file("s3://test-bucket/testfile.txt") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"

    def test_open_as_file_compressed(self):
        """It should be able to open a file from an S3 bucket."""
        with open_as_file("s3://test-bucket/testfile.txt.gz") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"


class TestZipAdapter:
    @pytest.fixture()
    def zip_archive_content(self, tmp_path: Path) -> Path:
        """
        Set up a ZIP archive containing test files.
        """
        zip_path = tmp_path / "archive.zip"

        # Create a text file to include in the ZIP archive
        text_file_path = tmp_path / "testfile.txt"
        with open(text_file_path, "w") as f:
            f.write("Hello, world!")

        # Create a ZIP archive and add the text file to it
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.write(text_file_path, arcname="testfile.txt")

        # Optionally, add more files to the ZIP archive
        another_file_path = tmp_path / "anothertestfile.txt"
        with open(another_file_path, "w") as f:
            f.write("Another file content")

        with zipfile.ZipFile(zip_path, "a") as zipf:
            zipf.write(another_file_path, arcname="anothertestfile.txt")

        set_config("adapters.zip.fo", str(zip_path))
        return zip_path

    def test_list_directory(self, zip_archive_content):
        """It should be able to list the contents of a zip archive."""
        assert list(expand_inputs("zip:///")) == [
            str("zip://anothertestfile.txt"),
            str("zip://testfile.txt"),
        ]

    def test_open_as_file(self, zip_archive_content):
        """It should be able to open a file from a URL."""
        with open_as_file("zip://testfile.txt") as fp:
            assert fp is not None
            assert fp.read() == b"Hello, world!"
