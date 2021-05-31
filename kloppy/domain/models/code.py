from dataclasses import dataclass, field
from typing import List, Dict

from kloppy.domain.models.common import DatasetType

from .common import Dataset, DataRecord
from ...utils import docstring_inherit_attributes


@dataclass
@docstring_inherit_attributes(DataRecord)
class Code(DataRecord):
    """
    Single code

    Attributes:
        id: identifier provided by the coding software
        code: string describing the code
        end_timestamp: float
        labels: Text labels describing this code instance

    """

    code_id: str
    code: str
    end_timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def start_timestamp(self):
        return self.timestamp


@dataclass
class CodeDataset(Dataset):
    records: List[Code]

    dataset_type: DatasetType = DatasetType.CODE

    @property
    def codes(self):
        return self.records


__all__ = ["Code", "CodeDataset"]
