from typing import Dict, Type

from ..core.builder import DatasetBuilder
from ...serializers.tracking import (
    TrackingDataSerializer,
    SkillCornerTrackingSerializer,
)


_DATASET_URLS = {match_id: {
                    'metadata': f'https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/match_data.json',
                    'raw_data': f'https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/structured_data.json'
                    }
                 for match_id in match_ids}

class SkillCornerTracking(DatasetBuilder):
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        game = kwargs.get("game", "game1")
        return _DATASET_URLS[game]

    def get_serializer_cls(self) -> Type[TrackingDataSerializer]:
        return SkillCornerTrackingSerializer
