from typing import Dict, Type, List

from ..core.builder import DatasetBuilder
from ...serializers.tracking import (
    TrackingDataSerializer,
    SkillCornerTrackingSerializer,
)


_skillcorner_match_ids = [4039, 3749, 3518, 3442, 2841, 2440, 2417, 2269, 2068]

_match_info_strings = [
    "ID: 4039 - Manchester City vs Liverpool on 2020-07-02",
    "ID: 3749 - Dortmund vs Bayern Munchen on 2020-05-26",
    "ID: 3518 - Juventus vs Inter on 2020-03-08",
    "ID: 3442 - Real Madrid vs FC Barcelona on 2020-03-01",
    "ID: 2841 - FC Barcelona vs Real Madrid on 2019-12-18",
    "ID: 2440 - Liverpool vs Manchester City on 2019-11-10",
    "ID: 2417 - Bayern Munchen vs Dortmund on 2019-11-09",
    "ID: 2269 - Paris vs Marseille on 2019-10-27",
    "ID: 2068 - Inter vs Juventus on 2019-10-06",
]

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

    def get_available_matches(self) -> List[str]:
        return _match_info_strings
