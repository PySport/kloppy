from abc import abstractmethod
from typing import Dict, Type, Union, Callable

from kloppy.domain import Dataset
from ...serializers.tracking import TrackingDataSerializer
from .registered import RegisteredDataset


class DatasetBuilder(metaclass=RegisteredDataset):
    @abstractmethod
    def get_dataset_urls(self, **kwargs) -> Dict[str, Dict[str, str]]:
        raise NotImplementedError

    @abstractmethod
    def loader(self) -> Callable[[], Dataset]:
        raise NotImplementedError
