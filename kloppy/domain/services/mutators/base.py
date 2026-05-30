from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from kloppy.domain import Dataset

D = TypeVar("D", bound=Dataset)


class DatasetMutator(ABC, Generic[D]):
    def __init__(self, *, inplace: bool = False):
        self.inplace = inplace

    def mutate(self, dataset: D) -> D:
        if self.inplace:
            return self._mutate_inplace(dataset)
        else:
            return self._mutate_inplace(self._copy_dataset(dataset))

    @abstractmethod
    def _mutate_inplace(self, dataset: D) -> D:
        raise NotImplementedError

    def _copy_dataset(self, dataset: D) -> D:
        from dataclasses import replace

        return replace(dataset, records=list(dataset.records))
