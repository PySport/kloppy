"""Module to store common fixtures. """

from pathlib import Path

import pytest


@pytest.fixture
def base_dir():
    return Path(__file__).parent
