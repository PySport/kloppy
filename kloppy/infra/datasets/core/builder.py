from abc import abstractmethod
from typing import Dict, Type, Union

from ...serializers.tracking import TrackingDataSerializer
from .registered import RegisteredDataset


class DatasetBuilder(metaclass=RegisteredDataset):
    @abstractmethod
    def get_dataset_urls(self, **kwargs) -> Dict[str, Dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def get_serializer_cls(self) -> Union[Type[TrackingDataSerializer]]:
        raise NotImplementedError
