from typing import Dict

from ..core.builder import DatasetBuilder
from ...serializers.tracking.metrica_csv import (
    MetricaCSVTrackingDataDeserializer,
    MetricaCSVTrackingDataInputs,
)

_DATASET_URLS = {
    "game1": {
        "home_data": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv",
        "away_data": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Away_Team.csv",
    },
    "game2": {
        "home_data": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_2/Sample_Game_2_RawTrackingData_Home_Team.csv",
        "away_data": "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data/Sample_Game_2/Sample_Game_2_RawTrackingData_Away_Team.csv",
    },
}


class MetricaTracking(DatasetBuilder):
    deserializer_cls = MetricaCSVTrackingDataDeserializer
    inputs_cls = MetricaCSVTrackingDataInputs

    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        game = kwargs.get("game", "game1")
        return _DATASET_URLS[game]
