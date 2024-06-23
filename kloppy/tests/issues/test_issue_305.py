from pathlib import Path

import pytest

from kloppy import tracab


@pytest.fixture(scope="session")
def json_meta_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta.json"


@pytest.fixture(scope="session")
def json_raw_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_raw.json"


@pytest.fixture(scope="session")
def xml_meta_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta.xml"


@pytest.fixture(scope="session")
def dat_raw_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_raw.dat"


class TestIssue305:
    def test_str_path_xml(self, xml_meta_data: Path, dat_raw_data: Path):
        dataset = tracab.load(
            meta_data=str(xml_meta_data),
            raw_data=str(dat_raw_data),
            coordinates="tracab",
            only_alive=False,
        )
        assert dataset

    def test_str_path_json(self, json_meta_data: Path, json_raw_data: Path):
        dataset = tracab.load(
            meta_data=str(json_meta_data),
            raw_data=str(json_raw_data),
            coordinates="tracab",
            only_alive=False,
        )
        assert dataset
