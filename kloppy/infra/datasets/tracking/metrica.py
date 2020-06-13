from typing import Dict, Type

from ..core.builder import DatasetBuilder
from ...serializers.tracking import (
    TrackingDataSerializer,
    MetricaTrackingSerializer,
)


_DATASET_URLS = {
    "game1": {
        "raw_data_home": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv",
        "raw_data_away": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Away_Team.csv",
    },
    "game2": {
        "raw_data_home": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_2/Sample_Game_2_RawTrackingData_Home_Team.csv",
        "raw_data_away": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_2/Sample_Game_2_RawTrackingData_Away_Team.csv",
    },
}


class MetricaTracking(DatasetBuilder):
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        game = kwargs.get("game", "game1")
        return _DATASET_URLS[game]

    def get_serializer_cls(self) -> Type[TrackingDataSerializer]:
        return MetricaTrackingSerializer
