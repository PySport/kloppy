"""Module to store common fixtures."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def base_dir() -> Path:
    return Path(__file__).parent


@pytest.fixture(scope="session")
def with_visualization(base_dir):
    enable_viz = os.environ.get("KLOPPY_TESTWITHVIZ") == "1"
    if enable_viz:
        (base_dir / "outputs").mkdir(exist_ok=True)
    return enable_viz
