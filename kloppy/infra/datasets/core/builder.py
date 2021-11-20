from abc import abstractmethod
from typing import Dict, Union, NamedTuple, Tuple, Type, Callable

from ...serializers.event.deserializer import EventDataDeserializer
from ...serializers.tracking.deserializer import TrackingDataDeserializer

from .registered import RegisteredDataset


class DatasetBuilder(metaclass=RegisteredDataset):
    @abstractmethod
    def get_dataset_urls(self, **kwargs) -> Dict[str, str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def deserializer_cls(
        self,
    ) -> Callable[..., Union[EventDataDeserializer, TrackingDataDeserializer]]:
        raise NotImplementedError

    @property
    @abstractmethod
    def inputs_cls(self) -> Type[NamedTuple]:
        raise NotImplementedError
