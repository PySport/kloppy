import sys
from abc import ABC, abstractmethod
from fnmatch import fnmatch
from typing import Any, Callable, Dict, Generic, Tuple, Type, TypeVar, Union

if sys.version_info >= (3, 11):
    from typing import Unpack
else:
    from typing_extensions import Unpack

from kloppy.domain import Code, DataRecord, DatasetType, Event, Frame
from kloppy.domain.services.transformers.attribute import (
    DefaultCodeTransformer,
    DefaultEventTransformer,
    DefaultFrameTransformer,
)
from kloppy.exceptions import KloppyError

T = TypeVar("T", bound=DataRecord)
Column = Union[str, Callable[[T], Any]]
NamedColumns = Dict[str, Column]


class DataRecordToDictTransformer(ABC, Generic[T]):
    @abstractmethod
    def default_transformer(self) -> Callable[[T], Dict]:
        ...

    def __init__(
        self,
        *columns: Unpack[Tuple[Column]],
        **named_columns: NamedColumns,
    ):
        if not columns and not named_columns:
            converter = self.default_transformer()
        else:
            default = self.default_transformer()
            has_string_columns = any(
                not callable(column) for column in columns
            )

            def converter(data_record: T) -> Dict[str, Any]:
                if has_string_columns:
                    default_row = default(data_record)
                else:
                    default_row = {}

                row = {}
                for column in columns:
                    if callable(column):
                        res = column(data_record)
                        if not isinstance(res, dict):
                            raise KloppyError(
                                "A function column should return a dictionary"
                            )
                        row.update(res)
                    else:
                        if column == "*":
                            row.update(default_row)
                        elif "*" in column:
                            row.update(
                                {
                                    k: v
                                    for k, v in default_row.items()
                                    if fnmatch(k, column)
                                }
                            )
                        elif column in default_row:
                            row[column] = default_row[column]
                        else:
                            row[column] = getattr(data_record, column, None)

                for name, column in named_columns.items():
                    row[name] = (
                        column(data_record) if callable(column) else column
                    )

                return row

        self.converter = converter

    def __call__(self, data_record: T) -> Dict[str, Any]:
        return self.converter(data_record)


class EventToDictTransformer(DataRecordToDictTransformer[Event]):
    def default_transformer(self) -> Callable[[Event], Dict]:
        return DefaultEventTransformer()


class FrameToDictTransformer(DataRecordToDictTransformer[Frame]):
    def default_transformer(self) -> Callable[[Frame], Dict]:
        return DefaultFrameTransformer()


class CodeToDictTransformer(DataRecordToDictTransformer[Code]):
    def default_transformer(self) -> Callable[[Code], Dict]:
        return DefaultCodeTransformer()


def get_transformer_cls(
    dataset_type: DatasetType,
) -> Type[DataRecordToDictTransformer]:
    if dataset_type == DatasetType.EVENT:
        return EventToDictTransformer
    elif dataset_type == DatasetType.TRACKING:
        return FrameToDictTransformer
    elif dataset_type == DatasetType.CODE:
        return CodeToDictTransformer
