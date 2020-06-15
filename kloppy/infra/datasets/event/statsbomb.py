import warnings
from typing import Dict, Type

from ..core.builder import DatasetBuilder
from ...serializers.event import EventDataSerializer, StatsBombSerializer


# 3749133 / 38412
class Statsbomb(DatasetBuilder):
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        warnings.warn(
            "\n\nYou are about to use StatsBomb public data."
            "\nBy using this data, you are agreeing to the user agreement. "
            "\nThe user agreement can be found here: https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf"
            "\n"
        )

        match_id = kwargs.get("match_id", "15946")
        return {
            "event_data": f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json",
            "lineup_data": f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/{match_id}.json",
        }

    def get_serializer_cls(self) -> Type[EventDataSerializer]:
        return StatsBombSerializer
