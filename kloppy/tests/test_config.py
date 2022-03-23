import os

import pytest
from kloppy import opta
from kloppy.config import set_config, get_config, config_context, reset_config
from kloppy.domain import KloppyCoordinateSystem, OptaCoordinateSystem


class TestConfig:
    @pytest.fixture(autouse=True)
    def tear_down(self):
        """Make sure all config changes are reverted for next tests."""
        try:
            yield
        finally:
            reset_config()

    @pytest.fixture
    def f24_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/opta_f24.xml"

    @pytest.fixture
    def f7_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/opta_f7.xml"

    def test_set_config(self, f24_data: str, f7_data: str):
        """
        Make sure the coordinate system can be set and is used
        when loading data.
        """
        dataset = opta.load(f24_data=f24_data, f7_data=f7_data)
        assert isinstance(
            dataset.metadata.coordinate_system, KloppyCoordinateSystem
        )

        set_config("coordinate_system", "opta")

        dataset = opta.load(f24_data=f24_data, f7_data=f7_data)
        assert isinstance(
            dataset.metadata.coordinate_system, OptaCoordinateSystem
        )

    def test_config_context(self, f24_data: str, f7_data: str):
        assert get_config("coordinate_system") == "kloppy"

        with config_context("coordinate_system", "opta"):
            assert get_config("coordinate_system") == "opta"

            dataset = opta.load(f24_data=f24_data, f7_data=f7_data)

        assert get_config("coordinate_system") == "kloppy"

        assert isinstance(
            dataset.metadata.coordinate_system, OptaCoordinateSystem
        )
