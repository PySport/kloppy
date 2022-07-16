from fnmatch import fnmatch
from typing import NewType, Union, Callable, Any, Dict

from kloppy.domain import Event
from kloppy.domain.services.transformers.attribute import DefaultTransformer
from kloppy.exceptions import KloppyError

Column = NewType("Column", Union[str, Callable[[Event], Any]])


class EventToRecordTransformer:
    def __init__(
        self,
        *columns: Column,
        **named_columns: Column,
    ):
        if not columns and not named_columns:

            converter = DefaultTransformer()
        else:
            default = DefaultTransformer()
            has_string_columns = any(
                not callable(column) for column in columns
            )

            def converter(event: Event) -> Dict[str, Any]:
                if has_string_columns:
                    default_row = default(event)
                else:
                    default_row = {}

                row = {}
                for column in columns:
                    if callable(column):
                        res = column(event)
                        if not isinstance(res, dict):
                            raise KloppyError(
                                f"A function column should return a dictionary"
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
                            row[column] = getattr(event, column, None)

                for name, column in named_columns.items():
                    row[name] = column(event) if callable(column) else column

                return row

        self.converter = converter

    def __call__(self, event: Event) -> Dict[str, Any]:
        return self.converter(event)
