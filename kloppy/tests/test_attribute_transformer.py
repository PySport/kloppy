import os

import pytest
from kloppy import statsbomb
from kloppy.domain import BodyPartQualifier
from kloppy.domain.services.transformers.attribute import BodyPartTransformer


class TestAttributeTransformer:
    @pytest.fixture
    def event_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsbomb_event.json"

    @pytest.fixture
    def lineup_data(self) -> str:
        base_dir = os.path.dirname(__file__)
        return f"{base_dir}/files/statsbomb_lineup.json"

    def test_correct_deserialization(self, lineup_data: str, event_data: str):
        """
        This test uses data from the StatsBomb open data project.
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            coordinates="statsbomb",
        )

        event = dataset.events[792]

        transformer = BodyPartTransformer()
        data = transformer.transform(event)
