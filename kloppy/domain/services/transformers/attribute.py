from abc import ABC, abstractmethod
import math
from typing import Dict, Any, Set, Type, Union, List, Optional

from kloppy.domain import (
    Event,
    BodyPartQualifier,
    DatasetTransformer,
    Orientation,
)
from kloppy.domain.models.event import (
    EnumQualifier,
    CarryEvent,
    PassEvent,
    EventType,
    ShotEvent,
    CardEvent,
)
from kloppy.exceptions import (
    UnknownEncoderError,
    OrientationError,
    KloppyParameterError,
)
from kloppy.utils import camelcase_to_snakecase


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


class AngleToGoalTransformer(EventAttributeTransformer):
    def __call__(self, event: Event) -> Dict[str, Any]:
        metadata = event.dataset.metadata
        if metadata.orientation != Orientation.ACTION_EXECUTING_TEAM:
            raise OrientationError(
                "Can only calculate Angle when dataset orientation is ACTION_EXECUTING_TEAM"
            )

        if not event.coordinates:
            return {"angle_to_goal": None}

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


class DistanceToGoalTransformer(EventAttributeTransformer):
    def __call__(self, event: Event) -> Dict[str, Any]:
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
    def __call__(self, event: Event) -> Dict[str, Any]:
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


class DefaultTransformer(EventAttributeTransformer):
    def __init__(
        self,
        *include: str,
        exclude: Optional[List[str]] = None,
    ):
        if include and exclude:
            raise KloppyParameterError(
                f"Cannot specify both include as exclude"
            )

        self.exclude = exclude or []
        self.include = include or []

    def __call__(self, event: Event) -> Dict[str, Any]:
        row = dict(
            event_id=event.event_id,
            event_type=(
                event.event_type.value
                if event.event_type != EventType.GENERIC
                else f"GENERIC:{event.event_name}"
            ),
            result=event.result.value if event.result else None,
            success=event.result.is_success if event.result else None,
            period_id=event.period.id,
            timestamp=event.timestamp,
            end_timestamp=None,
            ball_state=event.ball_state.value if event.ball_state else None,
            ball_owning_team=event.ball_owning_team.team_id
            if event.ball_owning_team
            else None,
            team_id=event.team.team_id if event.team else None,
            player_id=event.player.player_id if event.player else None,
            coordinates_x=event.coordinates.x if event.coordinates else None,
            coordinates_y=event.coordinates.y if event.coordinates else None,
        )
        if isinstance(event, PassEvent):
            row.update(
                {
                    "end_timestamp": event.receive_timestamp,
                    "end_coordinates_x": event.receiver_coordinates.x
                    if event.receiver_coordinates
                    else None,
                    "end_coordinates_y": event.receiver_coordinates.y
                    if event.receiver_coordinates
                    else None,
                    "receiver_player_id": event.receiver_player.player_id
                    if event.receiver_player
                    else None,
                }
            )
        elif isinstance(event, CarryEvent):
            row.update(
                {
                    "end_timestamp": event.end_timestamp,
                    "end_coordinates_x": event.end_coordinates.x
                    if event.end_coordinates
                    else None,
                    "end_coordinates_y": event.end_coordinates.y
                    if event.end_coordinates
                    else None,
                }
            )
        elif isinstance(event, ShotEvent):
            row.update(
                {
                    "end_coordinates_x": event.result_coordinates.x
                    if event.result_coordinates
                    else None,
                    "end_coordinates_y": event.result_coordinates.y
                    if event.result_coordinates
                    else None,
                }
            )
        elif isinstance(event, CardEvent):
            row.update(
                {
                    "card_type": event.card_type.value
                    if event.card_type
                    else None
                }
            )

        if event.qualifiers:
            for qualifier in event.qualifiers:
                row.update(qualifier.to_dict())

        if self.include:
            return {k: row[k] for k in self.include}
        elif self.exclude:
            return {k: v for k, v in row.items() if k not in self.exclude}
        else:
            return row


BodyPartTransformer = create_transformer_from_qualifier(BodyPartQualifier)
