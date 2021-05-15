from typing import Dict, Type, List

from ..core.builder import DatasetBuilder
from ...serializers.tracking import (
    TrackingDataSerializer,
    SkillCornerTrackingSerializer,
)


_skillcorner_match_ids = [4039, 3749, 3518, 3442, 2841, 2440, 2417, 2269, 2068]

_DATASET_URLS = {
    match_id: {
        "metadata": f"https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/match_data.json",
        "raw_data": f"https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/structured_data.json",
    }
    for match_id in _skillcorner_match_ids
}


class SkillCornerTracking(DatasetBuilder):
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        game = kwargs.get("game", 4039)
        return _DATASET_URLS[game]

    def get_serializer_cls(self) -> Type[TrackingDataSerializer]:
        return SkillCornerTrackingSerializer
