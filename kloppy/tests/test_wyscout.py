import os

import requests
from kloppy.domain import Provider, Point
from kloppy.infra.serializers.event.wyscout.serializer import WyscoutSerializer


class TestWyscout:
    def _load_dataset(self, options=None):
        base_dir = os.path.dirname(__file__)
        serializer = WyscoutSerializer()

        filename = os.path.join(base_dir, "files/wyscout_events.json")

        with open(os.path.join(base_dir, filename), "rb") as fd:
            dataset = serializer.deserialize(
                inputs={"event_data": fd}, options=options
            )
            return dataset

    def test_correct_deserialization(self):
        dataset = self._load_dataset(
            options={"coordinate_system": Provider.WYSCOUT}
        )
        df = dataset.to_pandas()
        print()
        print(df)

        assert dataset.records[10].coordinates == Point(23.0, 74.0)

    def test_correct_normalized_deserialization(self):
        dataset = self._load_dataset()
        df = dataset.to_pandas()
        print()
        print(df)

        assert dataset.records[10].coordinates == Point(0.23, 0.74)
