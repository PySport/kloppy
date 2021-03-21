from typing import Dict, Type
import urllib.request, json
from io import BytesIO

from ..core.builder import DatasetBuilder
from ...serializers.tracking import (
    TrackingDataSerializer,
    SkillCornerTrackingSerializer,
)


with urllib.request.urlopen('https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches.json') as url:
    skillcorner_match_info = json.load(BytesIO(url.read()))

skillcorner_match_ids = [m['id'] for m in skillcorner_match_info]
match_info_strings = [f"ID: {m['id']} - {m['home_team']['short_name']} vs {m['away_team']['short_name']}"
                      f" on {m['date_time'].split('T')[0]}" for m in skillcorner_match_info]

_DATASET_URLS = {match_id: {
                    'metadata': f'https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/match_data.json',
                    'raw_data': f'https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches/{match_id}/structured_data.json'
                    }
                 for match_id in skillcorner_match_ids}


class SkillCornerTracking(DatasetBuilder):
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        game = kwargs.get("game", 4039)
        return _DATASET_URLS[game]

    def get_serializer_cls(self) -> Type[TrackingDataSerializer]:
        return SkillCornerTrackingSerializer
