"""Module to store common fixtures. """

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def base_dir() -> Path:
    return Path(__file__).parent
