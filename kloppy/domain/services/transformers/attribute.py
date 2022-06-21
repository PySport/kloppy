from abc import ABC, abstractmethod
import math
from typing import Dict, Any, Set, Type, Union, List

from kloppy.domain import (
    Event,
    BodyPartQualifier,
    DatasetTransformer,
    Orientation,
)
from kloppy.domain.models.event import EnumQualifier
from kloppy.exceptions import UnknownEncoderError, OrientationError
from kloppy.utils import camelcase_to_snakecase


# class OneHotEncoder:
#     def __init__(self, name: str, options: List[str]):
#         self.options = options
#         self.name = name
#
#     def encode(self, value: str) -> Dict[str, bool]:
#         return {
#             f"is_{self.name}_{option_.lower()}": option_ == value
#             for option_ in self.options
#         }


class OneHotEncoder:
    def __init__(self, name: str, options: List[str]):
        self.options = options
        self.name = name

    def encode(self, value: Union[Set, str]) -> Dict[str, bool]:
        if isinstance(value, str):
            value = [value]

        return {
            f"is_{self.name}_{option_.lower()}": option_ in value
            for option_ in self.options
        }


class EventAttributeTransformer(ABC):
    @abstractmethod
    def __call__(self, event: Event) -> Dict[str, Any]:
        pass


class AngleToGoal(EventAttributeTransformer):
    def __call__(self, event: Event) -> Dict[str, Any]:
        metadata = event.dataset.metadata
        if metadata.orientation != Orientation.ACTION_EXECUTING_TEAM:
            raise OrientationError(
                "Can only calculate Angle when dataset orientation is ACTION_EXECUTING_TEAM"
            )

        if metadata.pitch_dimensions.width:
            # Calculate in metric system
            event_x = event.coordinates.x * metadata.pitch_dimensions.length
            event_y = event.coordinates.y * metadata.pitch_dimensions.width
            goal_x = metadata.pitch_dimensions.length
            goal_y = metadata.pitch_dimensions.width / 2
        else:
            event_x = event.coordinates.x
            event_y = event.coordinates.y
            goal_x = metadata.pitch_dimensions.x_dim.max
            goal_y = (
                metadata.pitch_dimensions.y_dim.max
                + metadata.pitch_dimensions.y_dim.min
            ) / 2

        return {
            "angle_to_goal": math.atan2(goal_x - event_x, goal_y - event_y)
            / math.pi
            * 180
        }


class DistanceToGoal(EventAttributeTransformer):
    def __call__(self, event: Event) -> Dict[str, Any]:
        metadata = event.dataset.metadata
        if metadata.orientation != Orientation.ACTION_EXECUTING_TEAM:
            raise OrientationError(
                "Can only calculate Angle when dataset orientation is ACTION_EXECUTING_TEAM"
            )

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


def create_transformer_from_qualifier(
    qualifier_type: Type[EnumQualifier],
) -> Type[EventAttributeTransformer]:
    enum_ = qualifier_type.__annotations__["value"]
    name = camelcase_to_snakecase(enum_.__name__)
    options = [e.value for e in enum_]

    class _Transformer(EventAttributeTransformer):
        def __init__(self, encoding: str = "one-hot"):
            if encoding == "one-hot":
                self.encoder = OneHotEncoder(name, options)
            else:
                raise UnknownEncoderError(f"Don't know {encoding} encoding")

        def __call__(self, event: Event) -> Dict[str, Any]:
            values = {
                qualifier.value.value
                for qualifier in event.qualifiers
                if isinstance(qualifier, qualifier_type)
            }
            return self.encoder.encode(values)

    return _Transformer


BodyPart = create_transformer_from_qualifier(BodyPartQualifier)
