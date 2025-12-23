"""Data Record Transformation.

This module provides tools for transforming kloppy DataRecord objects (such as
`Event`, `Frame`, and `Code`) into alternative formats like dictionaries, JSON
strings, or custom data structures.

It separates **data extraction** (getting values from the object) from
**formatting** (structuring the output). This allows the same underlying
extraction logic to support multiple layouts (e.g., wide vs. long for tracking
data formats) and target types (e.g., `dict` vs. `str`).

Key Components:
    TransformerRegistry: Maps `DatasetType` and layout names to transformer classes.
    DataRecordTransformer: Generic base class for extraction, filtering, and formatting.
    register_data_record_transformer: Decorator to register new transformers.

Examples:
    **1. Basic Transformation**
    Get a transformer for a specific DatasetType and convert a record to a list of dicts.

    >>> from kloppy.domain import DatasetType
    >>> from kloppy.domain.services.transformers.data_record import get_transformer_cls
    >>> # Default layout is implied
    >>> cls = get_transformer_cls(DatasetType.EVENT)
    >>> transformer = cls()
    >>> data = transformer(event)
    >>> # Result: [{'event_id': '...', 'timestamp': 0.1, ...}]

    **2. Column Selection & Wildcards**
    Filter the output using specific column names or wildcards.

    >>> # Select 'event_id' and any column containing 'coordinates'
    >>> transformer = cls("event_id", "*coordinates*")
    >>> data = transformer(event)

    **3. Custom Formatting (e.g., JSON)**
    Change the output type by providing a `formatter` callable.

    >>> import json
    >>> # Returns a list of JSON strings instead of dicts
    >>> transformer = cls(formatter=json.dumps)
    >>> json_data = transformer(event)
"""

from abc import ABC, abstractmethod
from fnmatch import fnmatch
import sys
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
)

if sys.version_info >= (3, 11):
    from typing import Unpack
else:
    from typing_extensions import Unpack

from kloppy.domain import (
    Code,
    DataRecord,
    DatasetType,
    Event,
    Frame,
    QualifierMixin,
    ResultMixin,
)
from kloppy.domain.models.event import (
    CardEvent,
    CarryEvent,
    EventType,
    PassEvent,
    ShotEvent,
)
from kloppy.exceptions import KloppyError

# --- Type Definitions ---

RecordT = TypeVar("RecordT", bound=DataRecord)
OutputT = TypeVar("OutputT")

# A column can be a name (str) or a logical function
ColumnSelector = Union[str, Callable[[RecordT], Any]]
NamedColumnDefinitions = dict[str, Union[Any, Callable[[RecordT], Any]]]


# --- Registry System ---


class TransformerRegistry:
    """Central registry for DataRecord transformers."""

    def __init__(self):
        # Structure: DatasetType -> Layout -> TransformerClass
        self._registry: dict[
            DatasetType, dict[str, type[DataRecordTransformer]]
        ] = {}

    def register(
        self,
        dataset_type: DatasetType,
        layout: Union[str, list[str]] = "default",
    ):
        """Decorator to register a transformer class."""
        layouts = [layout] if isinstance(layout, str) else layout

        def wrapper(cls):
            if dataset_type not in self._registry:
                self._registry[dataset_type] = {}

            for layout_name in layouts:
                current_map = self._registry[dataset_type]

                # Idempotency check
                if layout_name in current_map:
                    existing = current_map[layout_name]
                    if existing != cls:
                        raise KloppyError(
                            f"Conflict: '{layout_name}' for {dataset_type} is already "
                            f"registered to {existing.__name__}."
                        )

                current_map[layout_name] = cls
            return cls

        return wrapper

    def get_class(
        self, dataset_type: DatasetType, layout: Optional[str] = "default"
    ) -> type["DataRecordTransformer"]:
        """Retrieve a transformer class by type and layout."""
        layout = layout or "default"

        if dataset_type not in self._registry:
            raise KloppyError(
                f"No transformers registered for dataset type: {dataset_type}"
            )

        available = self._registry[dataset_type]
        if layout not in available:
            raise KloppyError(
                f"Layout '{layout}' not found for {dataset_type}. "
                f"Available: {list(available.keys())}"
            )
        return available[layout]


# Global instance
_REGISTRY = TransformerRegistry()

# Public API aliases for explicit naming
register_transformer = _REGISTRY.register
get_transformer_cls = _REGISTRY.get_class


# --- Base Transformer ---


class DataRecordTransformer(ABC, Generic[RecordT, OutputT]):
    """
    Base class for transforming DataRecords into a specific OutputT.

    This class orchestrates:
    1. Extraction (to a canonical dict)
    2. Filtering (selecting specific columns)
    3. Augmentation (adding named columns)
    4. Formatting (converting dict to OutputT)
    """

    def __init__(
        self,
        *columns: Unpack[tuple[ColumnSelector]],
        formatter: Optional[Callable[[dict[str, Any]], OutputT]] = None,
        **named_columns: NamedColumnDefinitions,
    ):
        """
        Args:
            *columns: Fields to select/compute.
            formatter: Optional function to convert the final dict to OutputT.
                       If None, the output remains a dict (OutputT = dict).
            **named_columns: New columns to append.
        """
        self.columns = columns
        self.named_columns = named_columns
        self.formatter = formatter

    def transform_record(self, record: RecordT) -> list[OutputT]:
        """Public API to transform a record."""
        # 1. Extract canonical data (List of Dictionaries)
        canonical_rows = self._extract_canonical(record)

        # 2. Process rows (Filter & Augment)
        processed_rows = [
            self._process_row(row, record) for row in canonical_rows
        ]

        # 3. Format output
        if self.formatter:
            return [self.formatter(row) for row in processed_rows]

        # If no formatter, we assume OutputT is dict
        return processed_rows  # type: ignore

    @abstractmethod
    def _extract_canonical(self, record: RecordT) -> list[dict[str, Any]]:
        """
        Implementation specific logic to extract raw data from the record.
        Must return a list of flat dictionaries.
        """
        pass

    def _process_row(
        self, base_row: dict[str, Any], record: RecordT
    ) -> dict[str, Any]:
        """Applies column selection (filtering) and named column augmentation."""

        # Optimization: If no columns specified, keep everything
        if not self.columns:
            row = base_row.copy()
        else:
            row = {}
            for col in self.columns:
                if callable(col):
                    # Callables merge their result into the row
                    res = col(record)
                    if not isinstance(res, dict):
                        raise KloppyError(
                            "Callable columns must return a dictionary."
                        )
                    row.update(res)
                elif col == "*":
                    row.update(base_row)
                elif "*" in col:
                    # Wildcard match
                    row.update(
                        {k: v for k, v in base_row.items() if fnmatch(k, col)}
                    )
                elif col in base_row:
                    row[col] = base_row[col]
                else:
                    # Fallback to record attribute
                    row[col] = getattr(record, col, None)

        # Apply named columns
        for name, value_or_func in self.named_columns.items():
            if callable(value_or_func):
                row[name] = value_or_func(record)
            else:
                row[name] = value_or_func

        return row

    def __call__(self, record: RecordT) -> list[OutputT]:
        return self.transform_record(record)


# --- Concrete Implementations ---


@register_transformer(DatasetType.EVENT, layout="default")
class EventTransformer(DataRecordTransformer[Event, Any]):
    """Transformer for Event data."""

    def _extract_canonical(self, record: Event) -> list[dict[str, Any]]:
        row: dict[str, Any] = dict(
            event_id=record.event_id,
            event_type=(
                record.event_type.value
                if record.event_type != EventType.GENERIC
                else f"GENERIC:{record.event_name}"
            ),
            period_id=record.period.id,
            timestamp=record.timestamp,
            end_timestamp=None,
            ball_state=record.ball_state.value if record.ball_state else None,
            ball_owning_team=(
                record.ball_owning_team.team_id
                if record.ball_owning_team
                else None
            ),
            team_id=record.team.team_id if record.team else None,
            player_id=record.player.player_id if record.player else None,
            coordinates_x=record.coordinates.x if record.coordinates else None,
            coordinates_y=record.coordinates.y if record.coordinates else None,
        )

        # Event-specific logic
        if isinstance(record, PassEvent):
            row.update(
                {
                    "end_timestamp": record.receive_timestamp,
                    "end_coordinates_x": record.receiver_coordinates.x
                    if record.receiver_coordinates
                    else None,
                    "end_coordinates_y": record.receiver_coordinates.y
                    if record.receiver_coordinates
                    else None,
                    "receiver_player_id": record.receiver_player.player_id
                    if record.receiver_player
                    else None,
                }
            )
        elif isinstance(record, CarryEvent):
            row.update(
                {
                    "end_timestamp": record.end_timestamp,
                    "end_coordinates_x": record.end_coordinates.x
                    if record.end_coordinates
                    else None,
                    "end_coordinates_y": record.end_coordinates.y
                    if record.end_coordinates
                    else None,
                }
            )
        elif isinstance(record, ShotEvent):
            row.update(
                {
                    "end_coordinates_x": record.result_coordinates.x
                    if record.result_coordinates
                    else None,
                    "end_coordinates_y": record.result_coordinates.y
                    if record.result_coordinates
                    else None,
                }
            )
        elif isinstance(record, CardEvent):
            row.update(
                {
                    "card_type": record.card_type.value
                    if record.card_type
                    else None
                }
            )

        if isinstance(record, QualifierMixin) and record.qualifiers:
            for qualifier in record.qualifiers:
                row.update(qualifier.to_dict())

        if isinstance(record, ResultMixin):
            row.update(
                {
                    "result": record.result.value if record.result else None,
                    "success": record.result.is_success
                    if record.result
                    else None,
                }
            )
        else:
            row.update(
                {
                    "result": None,
                    "success": None,
                }
            )

        return [row]


@register_transformer(DatasetType.TRACKING, layout=["wide", "default"])
class TrackingWideTransformer(DataRecordTransformer[Frame, Any]):
    """Wide-format transformer for Tracking data."""

    def _extract_canonical(self, record: Frame) -> list[dict[str, Any]]:
        row: dict[str, Any] = dict(
            period_id=record.period.id if record.period else None,
            timestamp=record.timestamp,
            frame_id=record.frame_id,
            ball_state=record.ball_state.value if record.ball_state else None,
            ball_owning_team_id=(
                record.ball_owning_team.team_id
                if record.ball_owning_team
                else None
            ),
            ball_x=record.ball_coordinates.x
            if record.ball_coordinates
            else None,
            ball_y=record.ball_coordinates.y
            if record.ball_coordinates
            else None,
            ball_z=getattr(record.ball_coordinates, "z", None)
            if record.ball_coordinates
            else None,
            ball_speed=record.ball_speed,
        )

        for player, player_data in record.players_data.items():
            # Flatten player data into columns
            prefix = f"{player.player_id}"
            row.update(
                {
                    f"{prefix}_x": player_data.coordinates.x
                    if player_data.coordinates
                    else None,
                    f"{prefix}_y": player_data.coordinates.y
                    if player_data.coordinates
                    else None,
                    f"{prefix}_d": player_data.distance,
                    f"{prefix}_s": player_data.speed,
                }
            )
            if player_data.other_data:
                for k, v in player_data.other_data.items():
                    row[f"{prefix}_{k}"] = v

        if record.other_data:
            row.update(record.other_data)

        return [row]


@register_transformer(DatasetType.TRACKING, layout="long")
class TrackingLongTransformer(DataRecordTransformer[Frame, Any]):
    """Long-format transformer for Tracking data."""

    def _extract_canonical(self, record: Frame) -> list[dict[str, Any]]:
        rows = []
        base_data = {
            "period_id": record.period.id if record.period else None,
            "timestamp": record.timestamp,
            "frame_id": record.frame_id,
            "ball_state": record.ball_state.value
            if record.ball_state
            else None,
            "ball_owning_team_id": (
                record.ball_owning_team.team_id
                if record.ball_owning_team
                else None
            ),
        }
        if record.other_data:
            base_data.update(record.other_data)

        # Ball
        ball_row = base_data.copy()
        ball_row.update(
            {
                "team_id": "ball",
                "player_id": "ball",
                "x": record.ball_coordinates.x
                if record.ball_coordinates
                else None,
                "y": record.ball_coordinates.y
                if record.ball_coordinates
                else None,
                "z": getattr(record.ball_coordinates, "z", None)
                if record.ball_coordinates
                else None,
                "s": record.ball_speed,
            }
        )
        rows.append(ball_row)

        # Players
        for player, player_data in record.players_data.items():
            p_row = base_data.copy()
            p_row.update(
                {
                    "team_id": player.team.team_id if player.team else None,
                    "player_id": player.player_id,
                    "x": player_data.coordinates.x
                    if player_data.coordinates
                    else None,
                    "y": player_data.coordinates.y
                    if player_data.coordinates
                    else None,
                    "z": getattr(player_data.coordinates, "z", None)
                    if player_data.coordinates
                    else None,
                    "d": player_data.distance,
                    "s": player_data.speed,
                }
            )
            if player_data.other_data:
                p_row.update(player_data.other_data)
            rows.append(p_row)

        return rows


@register_transformer(DatasetType.CODE, layout="default")
class CodeTransformer(DataRecordTransformer[Code, Any]):
    """Transformer for Code data."""

    def _extract_canonical(self, record: Code) -> list[dict[str, Any]]:
        row = dict(
            code_id=record.code_id,
            period_id=record.period.id if record.period else None,
            timestamp=record.timestamp,
            end_timestamp=record.end_timestamp,
            code=record.code,
        )
        row.update(record.labels)
        return [row]
