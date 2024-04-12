import os
from pathlib import Path

from kloppy.io import open_as_file, get_file_extension


class TestOpenAsFile:
    """Tests for the open_as_file function."""

    def test_bytes(self, base_dir: Path):
        """It should be able to open a file from a bytes object."""
        path = base_dir / "files" / "tracab_meta.xml"
        with open(path, "rb") as f:
            data = f.read()

        with open_as_file(data) as fp:
            assert fp.read() == data

    def test_str(self, base_dir: Path):
        """It should be able to open a file from a string object."""
        path = str(base_dir / "files" / "tracab_meta.xml")
        with open_as_file(path) as fp:
            data = fp.read()

        assert len(data) == os.path.getsize(path)

    def test_path(self, base_dir: Path):
        """It should be able to open a file from a Path object."""
        path = base_dir / "files" / "tracab_meta.xml"
        with open_as_file(path) as fp:
            data = fp.read()

        assert len(data) == os.path.getsize(path)

    def test_gzip(self, base_dir: Path, tmp_path: Path):
        """It should be able to open a gzipped file."""
        raw_path = base_dir / "files" / "tracab_meta.xml"
        gz_path = tmp_path / "tracab_meta.xml.gz"
        # Create a gzipped file
        import gzip

        with open(raw_path, "rb") as f:
            with gzip.open(gz_path, "wb") as f_out:
                f_out.write(f.read())
        # Read the gzipped file
        with open_as_file(raw_path) as fp:
            data = fp.read()

        assert len(data) == os.path.getsize(raw_path)

    def test_xz(self, base_dir: Path, tmp_path: Path):
        """It should be able to open a LZMA-compressed file."""
        raw_path = base_dir / "files" / "tracab_meta.xml"
        gz_path = tmp_path / "tracab_meta.xml.gz"
        # Create a LMZA-compressed file
        import lzma

        with open(raw_path, "rb") as f:
            with lzma.open(gz_path, "wb") as f_out:
                f_out.write(f.read())
        # Read the gzipped file
        with open_as_file(raw_path) as fp:
            data = fp.read()

        assert len(data) == os.path.getsize(raw_path)

    def test_bz2(self, base_dir: Path, tmp_path: Path):
        """It should be able to open a bzip2-compressed file."""
        raw_path = base_dir / "files" / "tracab_meta.xml"
        gz_path = tmp_path / "tracab_meta.xml.gz"
        # Create a bz2-compressed file
        import bz2

        with open(raw_path, "rb") as f:
            with bz2.open(gz_path, "wb") as f_out:
                f_out.write(f.read())
        # Read the gzipped file
        with open_as_file(raw_path) as fp:
            data = fp.read()

        assert len(data) == os.path.getsize(raw_path)


def test_get_file_extension():
    assert get_file_extension(Path("data.xml")) == ".xml"
    assert get_file_extension("data.xml") == ".xml"
    assert get_file_extension("data.xml.gz") == ".xml"
    assert get_file_extension("data") == ""
