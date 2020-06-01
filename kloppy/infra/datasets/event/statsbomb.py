from typing import Dict, Type

from ..core.builder import DatasetBuilder
from ...serializers.event import EventDataSerializer, StatsbombSerializer


# 3749133 / 38412
class Statsbomb(DatasetBuilder):
    def get_data_set_files(self,**kwargs) -> Dict[str, str]:
        match_id = kwargs.get('match_id', '15946')
        return {
            'raw_data': f'https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{match_id}.json',
            'lineup': f'https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/{match_id}.json'
        }

    def get_serializer_cls(self) -> Type[EventDataSerializer]:
        return StatsbombSerializer
