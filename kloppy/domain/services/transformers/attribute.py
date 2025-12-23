"""Event Attribute Transformation.

This module provides tools to extract, calculate, and encode features from
individual `Event` objects. These transformers are designed to enrich event data
with derived metrics (like distance to goal) or categorical encodings (like
one-hot encoded body parts) for downstream analysis or machine learning tasks.

Examples:
    **1. Calculating Distances and Angles**
    Compute spatial metrics for an event relative to the goal.

    >>> from kloppy.domain.models.event import ShotEvent
    >>> # event is a ShotEvent derived from a dataset with ACTION_EXECUTING_TEAM orientation
    >>>
    >>> dist_transformer = DistanceToGoalTransformer()
    >>> angle_transformer = AngleToGoalTransformer()
    >>>
    >>> features = {}
    >>> features.update(dist_transformer(event))
    >>> features.update(angle_transformer(event))
    >>> # features: {'distance_to_goal': 16.5, 'angle_to_goal': 25.4}

    **2. Encoding Qualifiers (Body Parts)**
    Convert categorical body part qualifiers into one-hot encoded columns.

    >>> from kloppy.domain import BodyPartQualifier
    >>> # event has a qualifier BodyPartQualifier(value=BodyPart.HEAD)
    >>>
    >>> transformer = BodyPartTransformer()
    >>> encoded = transformer(event)
    >>> # encoded: {'is_body_part_head': True, 'is_body_part_foot_right': False, ...}
"""

from abc import ABC, abstractmethod
import math
import sys
from typing import Any, Union

from kloppy.domain import (
    BodyPartQualifier,
    Event,
    Orientation,
    Point,
)
from kloppy.domain.models.event import (
    EnumQualifier,
)
from kloppy.exceptions import (
    OrientationError,
    UnknownEncoderError,
)
from kloppy.utils import camelcase_to_snakecase

py_version = sys.version_info
if py_version >= (3, 8):
    from typing import get_args


def _get_generic_type_arg(cls):
    t = cls.__orig_bases__[0]
    if py_version >= (3, 8):
        return get_args(t)[0]
    else:
        return t.__args__[0]


class OneHotEncoder:
    def __init__(self, name: str, options: list[str]):
        self.options = options
        self.name = name

    def encode(self, value: Union[set, str]) -> dict[str, bool]:
        if isinstance(value, str):
            value = [value]

        return {
            f"is_{self.name}_{option_.lower()}": option_ in value
            for option_ in self.options
        }


class EventAttributeTransformer(ABC):
    @abstractmethod
    def __call__(self, event: Event) -> dict[str, Any]:
        pass


class AngleToGoalTransformer(EventAttributeTransformer):
    def __call__(self, event: Event) -> dict[str, Any]:
        metadata = event.dataset.metadata
        if metadata.orientation != Orientation.ACTION_EXECUTING_TEAM:
            raise OrientationError(
                "Can only calculate Angle when dataset orientation is ACTION_EXECUTING_TEAM"
            )

        if not event.coordinates:
            return {"angle_to_goal": None}
        delta_x = metadata.pitch_dimensions.distance_between(
            Point(event.coordinates.x, 0),
            Point(metadata.pitch_dimensions.x_dim.max, 0),
        )
        delta_y = metadata.pitch_dimensions.distance_between(
            Point(0, event.coordinates.y),
            Point(
                0,
                (
                    metadata.pitch_dimensions.y_dim.max
                    + metadata.pitch_dimensions.y_dim.min
                )
                / 2,
            ),
        )

        return {"angle_to_goal": math.atan2(delta_x, delta_y) / math.pi * 180}


class DistanceToGoalTransformer(EventAttributeTransformer):
    def __call__(self, event: Event) -> dict[str, Any]:
        metadata = event.dataset.metadata
        if not event.coordinates:
            return {"distance_to_goal": None}

        event_x = event.coordinates.x
        event_y = event.coordinates.y
        goal_x = metadata.pitch_dimensions.x_dim.max
        goal_y = (
            metadata.pitch_dimensions.y_dim.max
            + metadata.pitch_dimensions.y_dim.min
        ) / 2

        return {
            "distance_to_goal": math.sqrt(
                (goal_x - event_x) ** 2 + (goal_y - event_y) ** 2
            )
        }


class DistanceToOwnGoalTransformer(EventAttributeTransformer):
    def __call__(self, event: Event) -> dict[str, Any]:
        metadata = event.dataset.metadata

        if not event.coordinates:
            return {"distance_to_own_goal": None}

        event_x = event.coordinates.x
        event_y = event.coordinates.y
        goal_x = metadata.pitch_dimensions.x_dim.min
        goal_y = (
            metadata.pitch_dimensions.y_dim.max
            + metadata.pitch_dimensions.y_dim.min
        ) / 2

        return {
            "distance_to_own_goal": math.sqrt(
                (goal_x - event_x) ** 2 + (goal_y - event_y) ** 2
            )
        }


def create_transformer_from_qualifier(
    qualifier_type: type[EnumQualifier],
) -> type[EventAttributeTransformer]:
    enum_ = _get_generic_type_arg(qualifier_type)
    name = camelcase_to_snakecase(enum_.__name__)
    options = [e.value for e in enum_]

    class _Transformer(EventAttributeTransformer):
        def __init__(self, encoding: str = "one-hot"):
            if encoding == "one-hot":
                self.encoder = OneHotEncoder(name, options)
            else:
                raise UnknownEncoderError(f"Don't know {encoding} encoding")

        def __call__(self, event: Event) -> dict[str, Any]:
            values = {
                qualifier.value.value
                for qualifier in event.qualifiers
                if isinstance(qualifier, qualifier_type)
            }
            return self.encoder.encode(values)

    return _Transformer


BodyPartTransformer = create_transformer_from_qualifier(BodyPartQualifier)
