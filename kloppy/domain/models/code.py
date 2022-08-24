from dataclasses import dataclass, field
from typing import List, Dict, Callable, Union, Any

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
    labels: Dict[str, Union[bool, str]] = field(default_factory=dict)

    @property
    def record_id(self) -> str:
        return self.record_id

    @property
    def start_timestamp(self):
        return self.timestamp


@dataclass
class CodeDataset(Dataset[Code]):
    records: List[Code]

    dataset_type: DatasetType = DatasetType.CODE

    @property
    def codes(self):
        return self.records

    def to_pandas(
        self,
        record_converter: Callable[[Code], Dict] = None,
        additional_columns: Dict[
            str, Union[Callable[[Code], Any], Any]
        ] = None,
    ) -> "DataFrame":
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Seems like you don't have pandas installed. Please"
                " install it using: pip install pandas"
            )

        if not record_converter:

            def record_converter(code: Code) -> Dict:
                row = dict(
                    code_id=code.code_id,
                    period_id=code.period.id if code.period else None,
                    timestamp=code.timestamp,
                    end_timestamp=code.end_timestamp,
                    code=code.code,
                )
                row.update(code.labels)

                return row

        def generic_record_converter(code: Code):
            row = record_converter(code)
            if additional_columns:
                for k, v in additional_columns.items():
                    if callable(v):
                        value = v(code)
                    else:
                        value = v
                    row.update({k: value})

            return row

        return pd.DataFrame.from_records(
            map(generic_record_converter, self.records)
        )


__all__ = ["Code", "CodeDataset"]
