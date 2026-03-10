from dataclasses import dataclass, field
from datetime import timedelta
from typing import Union

from kloppy.domain.models.common import DatasetType
from kloppy.utils import (
    docstring_inherit_attributes,
)

from .common import DataRecord, Dataset


@dataclass
@docstring_inherit_attributes(DataRecord)
class Code(DataRecord):
    """
    Single code

    Attributes:
        code_id: Unique identifier provided by the coding software. Aias for `record_id`.
        code: A string describing the code.
        end_timestamp: End timestamp for the period of time this code instance is active.
        labels: Text labels describing this code instance.
    """

    code_id: str
    code: str
    end_timestamp: timedelta
    labels: dict[str, Union[bool, str]] = field(default_factory=dict)

    @property
    def record_id(self) -> str:
        return self.record_id

    @property
    def start_timestamp(self):
        return self.timestamp


@dataclass
class CodeDataset(Dataset[Code]):
    """
    A dataset containing SportsCode annotations.

    Attributes:
        dataset_type (DatasetType): `"DatasetType.CODE"`
        codes (List[Code]): A list of codes. Alias for `records`.
        metadata (Metadata): Metadata of the code dataset.
    """

    dataset_type: DatasetType = DatasetType.CODE

    @property
    def codes(self):
        return self.records


__all__ = ["Code", "CodeDataset"]
