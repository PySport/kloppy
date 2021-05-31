from typing import Dict, Type

from ..core.builder import DatasetBuilder
from ...serializers.event import EventDataSerializer, WyscoutSerializer


class Wyscout(DatasetBuilder):
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        match_id = kwargs.get("match_id", "2499841")
        return {
            "event_data": f"https://raw.githubusercontent.com/koenvo/wyscout-soccer-match-event-dataset/main/processed/files/{match_id}.json",
        }

    def get_serializer_cls(self) -> Type[EventDataSerializer]:
        return WyscoutSerializer
