import os
from typing import BinaryIO

import pytest
from kloppy import opta
from kloppy.config import config_context
from kloppy.domain import Provider, DatasetType
from kloppy.exceptions import InputNotFoundError
from kloppy.infra.io.adapters import Adapter, adapters


class TestAdapter:
    @pytest.fixture
    def f24_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/opta_f24.xml"

    @pytest.fixture
    def f7_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/opta_f7.xml"

    def test_custom_adapter(self, f24_data: str, f7_data: str):
        """
        Make sure the coordinate system can be set and is used
        when loading data.
        """

        class CustomAdapter(Adapter):
            def supports(self, url: str) -> bool:
                return url.startswith("test123://")

            def read_to_stream(self, url: str, output: BinaryIO):
                if url == "test123://f24":
                    fp = open(f24_data, "rb")
                elif url == "test123://f7":
                    fp = open(f7_data, "rb")
                else:
                    raise Exception(f"Unknown url {url}")

                output.write(fp.read())
                fp.close()

        with config_context("cache", None):
            with pytest.raises(InputNotFoundError):
                # When our adapter is not registered yet
                # kloppy will fall back to regular `open`.
                opta.load(f24_data="test123://f24", f7_data="test123://f7")

            custom_adapter = CustomAdapter()
            adapters.append(custom_adapter)

            dataset = opta.load(
                f24_data="test123://f24", f7_data="test123://f7"
            )

            # cleanup
            adapters.remove(custom_adapter)

            # Asserts borrowed from `test_opta.py`
            assert dataset.metadata.provider == Provider.OPTA
            assert dataset.dataset_type == DatasetType.EVENT
            assert len(dataset.events) == 21
