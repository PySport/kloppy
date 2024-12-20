from datetime import timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable, Union, Any

from kloppy.domain.models.common import DatasetType

from .common import Dataset, DataRecord
from kloppy.utils import (
    docstring_inherit_attributes,
    deprecated,
)


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
    labels: Dict[str, Union[bool, str]] = field(default_factory=dict)

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

    @deprecated(
        "to_pandas will be removed in the future. Please use to_df instead."
    )
    def to_pandas(
        self,
        record_converter: Optional[Callable[[Code], Dict]] = None,
        additional_columns: Optional[
            Dict[str, Union[Callable[[Code], Any], Any]]
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
            from ..services.transformers.attribute import (
                DefaultCodeTransformer,
            )

            record_converter = DefaultCodeTransformer()

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
