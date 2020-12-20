import os

from kloppy.infra.serializers.event.wyscout.serializer import WyscoutSerializer


class TestWyscout:
    def _load_dataset(self, options=None):
        base_dir = os.path.dirname(__file__)
        serializer = WyscoutSerializer()

        with open(
            os.path.join(base_dir, "files/wyscout_events.json"), "rb"
        ) as fd:
            dataset = serializer.deserialize(inputs={"event_data": fd})
            return dataset

    def test_correct_deserialization(self):
        dataset = self._load_dataset()
        print(dataset)
