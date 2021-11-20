from typing import Dict

from ..core.builder import DatasetBuilder
from ...serializers.event.wyscout import WyscoutDeserializer, WyscoutInputs


class Wyscout(DatasetBuilder):
    deserializer_cls = WyscoutDeserializer
    inputs_cls = WyscoutInputs

    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        match_id = kwargs.get("match_id", "2499841")
        return {
            "event_data": f"https://raw.githubusercontent.com/koenvo/wyscout-soccer-match-event-dataset/main/processed/files/{match_id}.json",
        }
