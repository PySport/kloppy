import os

import requests
from kloppy.infra.serializers.event.wyscout.serializer import WyscoutSerializer


class TestWyscout:
    def _load_dataset(self, options=None):
        base_dir = os.path.dirname(__file__)
        serializer = WyscoutSerializer()

        filename = os.path.join(base_dir, "files/wyscout_events.json")

        with open(os.path.join(base_dir, filename), "rb") as fd:
            dataset = serializer.deserialize(inputs={"event_data": fd})
            return dataset

    def test_correct_deserialization(self):
        dataset = self._load_dataset()
        df = dataset.to_pandas()
        print()
        print(df)
