from typing import Tuple

from ...domain.models import DataSet
from ..utils import Readable
from . import TrackingDataSerializer


class TRACABSerializer(TrackingDataSerializer):
    def deserialize(self, data: Readable, metadata: Readable) -> DataSet:
        pass

    def serialize(self, data_set: DataSet) -> Tuple[str, str]:
        raise NotImplementedError

