from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import (
    Dict,
    List,
    Type,
    Union,
    Any,
    Callable,
    Optional,
    TypeVar,
    Generic,
    TYPE_CHECKING,
)

from kloppy.domain.models.common import (
    DatasetType,
    AttackingDirection,
    OrientationError,
    PositionType,
)
from kloppy.domain.models.time import Time
from kloppy.utils import (
    camelcase_to_snakecase,
    removes_suffix,
    docstring_inherit_attributes,
    deprecated,
    DeprecatedEnumValue,
)

from .common import DataRecord, Dataset, Player, Team
from .formation import FormationType
from .pitch import Point

from ...exceptions import OrphanedRecordError, InvalidFilterError, KloppyError

if TYPE_CHECKING:
    from .tracking import Frame

QualifierType = TypeVar("QualifierType")
EnumQualifierType = TypeVar("EnumQualifierType", bound=Enum)


class ResultType(Enum):
    @property
    @abstractmethod
    def is_success(self):
        raise NotImplementedError

    def __str__(self):
        return self.value


class ShotResult(ResultType):
    """
    ShotResult

    Attributes:
        GOAL (ShotResult): Shot resulted in a goal
        OFF_TARGET (ShotResult): Shot was off target
        POST (ShotResult): Shot hit the post
        BLOCKED (ShotResult): Shot was blocked by another player
        SAVED (ShotResult): Shot was saved by the keeper
    """

    GOAL = "GOAL"
    OFF_TARGET = "OFF_TARGET"
    POST = "POST"
    BLOCKED = "BLOCKED"
    SAVED = "SAVED"
    OWN_GOAL = "OWN_GOAL"

    @property
    def is_success(self):
        """
        Returns if the shot was a goal
        """
        return self == self.GOAL


class PassResult(ResultType):
    """
    PassResult

    Attributes:
        COMPLETE (PassResult): Complete pass
        INCOMPLETE (PassResult): Incomplete pass (intercepted)
        OUT (PassResult): Ball went out
        OFFSIDE (PassResult): Offside
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    OUT = "OUT"
    OFFSIDE = "OFFSIDE"

    @property
    def is_success(self):
        """
        Returns if the pass was complete
        """
        return self == self.COMPLETE


class TakeOnResult(ResultType):
    """
    TakeOnResult

    Attributes:
        COMPLETE (TakeOnResult): Complete take-on
        INCOMPLETE (TakeOnResult): Incomplete take-on
        OUT (TakeOnResult): Ball went out
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    OUT = "OUT"

    @property
    def is_success(self):
        """
        Returns if the take-on was complete
        """
        return self == self.COMPLETE


class CarryResult(ResultType):
    """
    CarryResult

    Attributes:
        COMPLETE (CarryResult): Complete carry
        INCOMPLETE (CarryResult): Incomplete carry
    """

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"

    @property
    def is_success(self):
        """
        Returns if the carry was complete
        """
        return self == self.COMPLETE


class DuelResult(ResultType):
    """
    DuelResult

    Attributes:
        WON (DuelResult): When winning the duel (player touching the ball first)
        LOST (DuelResult): When losing the duel (opponent touches the ball first)
        NEUTRAL (DuelResult): When neither player wins duel [Mainly for WyScout v2]
    """

    WON = "WON"
    LOST = "LOST"
    NEUTRAL = "NEUTRAL"

    @property
    def is_success(self):
        """
        Returns if the duel was won
        """
        return self == self.WON


class InterceptionResult(ResultType):
    """
    InterceptionResult

    Attributes:
        SUCCESS (InterceptionResult): An interception that gains possession of the ball (without going out of bounds)
        LOST (InterceptionResult): An interception by the defending team that knocked the ball to an attacker
        OUT (InterceptionResult): An interception that knocked the ball out of bounds
    """

    SUCCESS = "SUCCESS"
    LOST = "LOST"
    OUT = "OUT"

    @property
    def is_success(self):
        """
        Returns if the interception was successful
        """
        return self == self.SUCCESS


class CardType(Enum):
    """
    CardType

    Attributes:
        FIRST_YELLOW (CardType): First yellow card
        SECOND_YELLOW (CardType): Second yellow card
        RED (CardType): Red card
    """

    FIRST_YELLOW = "FIRST_YELLOW"
    SECOND_YELLOW = "SECOND_YELLOW"
    RED = "RED"


class EventType(Enum):
    """
    Attributes:
        GENERIC (EventType): Unrecognised event type
        PASS (EventType):
        SHOT (EventType):
        TAKE_ON (EventType):
        CARRY (EventType):
        CLEARANCE (EventType):
        INTERCEPTION (EventType):
        DUEL (EventType):
        SUBSTITUTION (EventType):
        CARD (EventType):
        PLAYER_ON (EventType):
        PLAYER_OFF (EventType):
        RECOVERY (EventType):
        MISCONTROL (EventType):
        BALL_OUT (EventType):
        FOUL_COMMITTED (EventType):
        GOALKEEPER (EventType):
        PRESSURE (EventType):
        FORMATION_CHANGE (EventType):
    """

    GENERIC = "generic"

    PASS = "PASS"
    SHOT = "SHOT"
    TAKE_ON = "TAKE_ON"
    CARRY = "CARRY"
    CLEARANCE = "CLEARANCE"
    INTERCEPTION = "INTERCEPTION"
    DUEL = "DUEL"
    SUBSTITUTION = "SUBSTITUTION"
    CARD = "CARD"
    PLAYER_ON = "PLAYER_ON"
    PLAYER_OFF = "PLAYER_OFF"
    RECOVERY = "RECOVERY"
    MISCONTROL = "MISCONTROL"
    BALL_OUT = "BALL_OUT"
    FOUL_COMMITTED = "FOUL_COMMITTED"
    GOALKEEPER = "GOALKEEPER"
    PRESSURE = "PRESSURE"
    FORMATION_CHANGE = "FORMATION_CHANGE"

    def __repr__(self):
        return self.value


@dataclass
class Qualifier(Generic[QualifierType], ABC):
    """
    An event qualifier.

    Qualifiers are linked to events and provide more detailed information
    about the specific event that occurred. Each event can have a series of
    qualifiers describing it.

    Attributes:
        name (str): The name of the qualifier.
        value (object, optional): Contains any related information.
    """

    value: QualifierType

    @abstractmethod
    def to_dict(self) -> Dict[str, QualifierType]:
        """
        Return the qualifier as a dict.
        """

    @property
    def name(self):
        return camelcase_to_snakecase(
            removes_suffix(type(self).__name__, "Qualifier")
        )


@dataclass
class BoolQualifier(Qualifier[bool], ABC):
    """
    An event qualifier with a true/false value.
    """

    def to_dict(self) -> Dict[str, bool]:
        return {f"is_{self.name}": self.value}


class EnumQualifier(
    Qualifier[EnumQualifierType], Generic[EnumQualifierType], ABC
):
    """
    An event qualifier with a set of possible values.
    """

    def to_dict(self) -> Dict[str, EnumQualifierType]:
        return {f"{self.name}_type": self.value}


class SetPieceType(Enum):
    """
    SetPieceType

    Attributes:
        GOAL_KICK (SetPieceType): A goal kick.
        FREE_KICK (SetPieceType): A free kick.
        THROW_IN (SetPieceType): A throw in.
        CORNER_KICK (SetPieceType): A corner kick.
        PENALTY (SetPieceType): A penalty kick.
        KICK_OFF (SetPieceType): A kick off at the beginning of a match or after scoring.
    """

    GOAL_KICK = "GOAL_KICK"
    FREE_KICK = "FREE_KICK"
    THROW_IN = "THROW_IN"
    CORNER_KICK = "CORNER_KICK"
    PENALTY = "PENALTY"
    KICK_OFF = "KICK_OFF"


@dataclass
class SetPieceQualifier(EnumQualifier[SetPieceType]):
    """
    Indicates that a pass or shot was a set piece.

    Attributes:
        name (str): `"set_piece"`
        value (SetPieceType): The type of set piece
    """


@dataclass
class CardQualifier(EnumQualifier[CardType]):
    """
    Indicates that a card was given.

    Attributes:
        name (str): `"card"`
        value (CardType): Specifies the type of card.
    """


class PassType(Enum):
    """
    PassType

    Attributes:
        CROSS (PassType): A ball played in from wide areas into the box.
        HAND_PASS (PassType): A pass given with a player’s hand.
        HEAD_PASS (PassType): A pass given with a player's head.
        HIGH_PASS (PassType): A pass that goes above shoulder level at peak height.
        LAUNCH (PassType): A long forward pass that does not appear to have a specific target.
        SIMPLE_PASS (PassType): A standard pass without complex maneuvers.
        SMART_PASS (PassType): A creative and penetrative pass attempting to break defensive lines.
        LONG_BALL (PassType): A pass that travels at least 32 meters.
        THROUGH_BALL (PassType): A pass played into space behind the defense.
        CHIPPED_PASS (PassType): A pass lifted into the air.
        FLICK_ON (PassType): A pass where a player 'flicks' the ball on towards a teammate using their head.
        ASSIST (PassType): A pass leading directly to a goal.
        ASSIST_2ND (PassType): A pass leading to another pass which then leads to a goal.
        SWITCH_OF_PLAY (PassType): Any pass which crosses the centre zone of the pitch and in length travels more than 50% of the width of the pitch.
    """

    CROSS = "CROSS"
    HAND_PASS = "HAND_PASS"
    HEAD_PASS = "HEAD_PASS"
    HIGH_PASS = "HIGH_PASS"
    LAUNCH = "LAUNCH"
    SIMPLE_PASS = "SIMPLE_PASS"
    SMART_PASS = "SMART_PASS"
    LONG_BALL = "LONG_BALL"
    THROUGH_BALL = "THROUGH_BALL"
    CHIPPED_PASS = "CHIPPED_PASS"
    FLICK_ON = "FLICK_ON"
    SHOT_ASSIST = "SHOT_ASSIST"
    ASSIST = "ASSIST"
    ASSIST_2ND = "ASSIST_2ND"
    SWITCH_OF_PLAY = "SWITCH_OF_PLAY"


@dataclass
class PassQualifier(EnumQualifier[PassType]):
    """
    Specifies the pass type.

    Attributes:
        name (str): `"pass"`
        value (PassType): The pass type.
    """


class BodyPart(Enum):
    """
    BodyPart

    Attributes:
        RIGHT_FOOT (BodyPart): Pass or Shot with right foot, save with right foot (for goalkeepers).
        LEFT_FOOT (BodyPart): Pass or Shot with left foot, save with left foot (for goalkeepers).
        HEAD (BodyPart): Pass or Shot with head, save with head (for goalkeepers).
        OTHER (BodyPart): Other body part (chest, back, etc.), for Pass and Shot.
        HEAD_OTHER (BodyPart): Pass or Shot with head or other body part. Only used when the data provider does not distinguish between HEAD and OTHER.
        BOTH_HANDS (BodyPart): Goalkeeper only. Save with both hands.
        CHEST (BodyPart): Goalkeeper only. Save with chest.
        LEFT_HAND (BodyPart): Goalkeeper only. Save with left hand.
        RIGHT_HAND (BodyPart): Goalkeeper only. Save with right hand.
        DROP_KICK (BodyPart): Pass is a keeper drop kick.
        KEEPER_ARM (BodyPart): Pass thrown from keepers hands.
        NO_TOUCH (BodyPart): Pass only. A player deliberately let the pass go past him instead of receiving it to deliver to a teammate behind him. (Also known as a "dummy").
    """

    RIGHT_FOOT = "RIGHT_FOOT"
    LEFT_FOOT = "LEFT_FOOT"
    HEAD = "HEAD"
    OTHER = "OTHER"
    HEAD_OTHER = "HEAD_OTHER"

    BOTH_HANDS = "BOTH_HANDS"
    CHEST = "CHEST"
    LEFT_HAND = "LEFT_HAND"
    RIGHT_HAND = "RIGHT_HAND"
    DROP_KICK = "DROP_KICK"
    KEEPER_ARM = "KEEPER_ARM"

    NO_TOUCH = "NO_TOUCH"


@dataclass
class BodyPartQualifier(EnumQualifier[BodyPart]):
    """
    Specifies the body part used to perform an action.

    Attributes:
        name (str): `"body_part"`
        value (BodyPart): The body part.
    """


class GoalkeeperAction(Enum):
    """
    Deprecated: GoalkeeperAction has been renamed to GoalkeeperActionType.

    Attributes:
        SAVE (GoalkeeperAction): Goalkeeper faces shot and saves.
        CLAIM (GoalkeeperAction): Goalkeeper catches cross.
        PUNCH (GoalkeeperAction): Goalkeeper punches ball clear.
        PICK_UP (GoalkeeperAction): Goalkeeper picks up ball.
        SMOTHER (GoalkeeperAction): Goalkeeper coming out to dispossess a player, equivalent to a tackle for an outfield player.
        REFLEX (GoalkeeperAction): Goalkeeper performs a reflex to save a ball.
        SAVE_ATTEMPT (GoalkeeperAction): Goalkeeper attempting to save a shot.
    """

    SAVE = DeprecatedEnumValue("SAVE")
    CLAIM = DeprecatedEnumValue("CLAIM")
    PUNCH = DeprecatedEnumValue("PUNCH")
    PICK_UP = DeprecatedEnumValue("PICK_UP")
    SMOTHER = DeprecatedEnumValue("SMOTHER")
    REFLEX = DeprecatedEnumValue("REFLEX")
    SAVE_ATTEMPT = DeprecatedEnumValue("SAVE_ATTEMPT")


class GoalkeeperActionType(Enum):
    """
    GoalkeeperActionType

    Attributes:
        SAVE (GoalkeeperActionType): Goalkeeper faces shot and saves.
        CLAIM (GoalkeeperActionType): Goalkeeper catches cross.
        PUNCH (GoalkeeperActionType): Goalkeeper punches ball clear.
        PICK_UP (GoalkeeperActionType): Goalkeeper picks up ball.
        SMOTHER (GoalkeeperActionType): Goalkeeper coming out to dispossess a player, equivalent to a tackle for an outfield player.
        REFLEX (GoalkeeperActionType): Goalkeeper performs a reflex to save a ball.
        SAVE_ATTEMPT (GoalkeeperActionType): Goalkeeper attempting to save a shot.
    """

    SAVE = "SAVE"
    CLAIM = "CLAIM"
    PUNCH = "PUNCH"
    PICK_UP = "PICK_UP"
    SMOTHER = "SMOTHER"

    REFLEX = "REFLEX"
    SAVE_ATTEMPT = "SAVE_ATTEMPT"


@dataclass
class GoalkeeperQualifier(EnumQualifier[GoalkeeperActionType]):
    """
    Specifies the goalkeeper action type.

    Attributes:
        name (str): `"goalkeeper"`
        value (GoalkeeperActionType): The goal keeper action type.
    """


class DuelType(Enum):
    """
    DuelType

    Attributes:
        AERIAL (DuelType): A duel when the ball is in the air and loose.
        GROUND (DuelType): A duel when the ball is on the ground.
        LOOSE_BALL (DuelType): When the ball is not under the control of any particular player or team.
        SLIDING_TACKLE (DuelType): A duel where the player slides on the ground to kick the ball away from an opponent.
    """

    AERIAL = "AERIAL"
    GROUND = "GROUND"
    LOOSE_BALL = "LOOSE_BALL"
    SLIDING_TACKLE = "SLIDING_TACKLE"
    TACKLE = "TACKLE"


@dataclass
class DuelQualifier(EnumQualifier[DuelType]):
    """
    Specifies the duel type.

    Attributes:
        name (str): `"duel"`
        value (DuelType): The duel type.
    """


@dataclass
class CounterAttackQualifier(BoolQualifier):
    """
    Indicates whether an event was part of a counter attack.

    Attributes:
        name (str): `"body_part"`
        value (BoolQualifier): True if the event was part of a counter attack; otherwise False.
    """


@dataclass
@docstring_inherit_attributes(DataRecord)
class Event(DataRecord, ABC):
    """
    Abstract event baseclass. All other event classes inherit from this class.

    Attributes:
        event_id: Event identifier given by provider. Alias for `record_id`.
        event_type: Type of event.
        event_name: Name of the event type.
        team: Team related to the event.
        player: Player related to the event.
        coordinates: Coordinates where event happened.
        result: Outcome of the event.
        attacking_direction: Attacking direction of `team`.
        raw_event: The data provider's raw representation of the event.
        state: Additional game state information.
        related_event_ids: Event identifiers of related events.
        qualifiers: Event qualifiers.
        freeze_frame: A snapshot with the location of other players at the time of the event.
    """

    event_id: str
    team: Team
    player: Player
    coordinates: Point

    result: Optional[ResultType]

    raw_event: object
    state: Dict[str, Any]
    related_event_ids: List[str]

    qualifiers: List[Qualifier]

    freeze_frame: Optional["Frame"]

    @property
    def record_id(self) -> str:
        return self.event_id

    @property
    @abstractmethod
    def event_type(self) -> EventType:
        raise NotImplementedError

    @property
    @abstractmethod
    def event_name(self) -> str:
        raise NotImplementedError

    @property
    def attacking_direction(self):
        if (
            self.dataset
            and self.dataset.metadata
            and self.dataset.metadata.orientation is not None
        ):
            try:
                return AttackingDirection.from_orientation(
                    self.dataset.metadata.orientation,
                    period=self.period,
                    ball_owning_team=self.ball_owning_team,
                    action_executing_team=self.team,
                )
            except OrientationError:
                return AttackingDirection.NOT_SET
        return AttackingDirection.NOT_SET

    def get_qualifier_value(self, qualifier_type: Type[Qualifier]):
        """
        Returns the Qualifier of a certain type, or None if qualifier is not present.

        Arguments:
            qualifier_type: one of the following QualifierTypes: [`SetPieceQualifier`][kloppy.domain.models.event.SetPieceQualifier]
                [`BodyPartQualifier`][kloppy.domain.models.event.BodyPartQualifier] [`PassQualifier`][kloppy.domain.models.event.PassQualifier]

        Examples:
            >>> from kloppy.domain import SetPieceQualifier
            >>> pass_event.get_qualifier_value(SetPieceQualifier)
            <SetPieceType.GOAL_KICK: 'GOAL_KICK'>
        """
        if self.qualifiers:
            for qualifier in self.qualifiers:
                if isinstance(qualifier, qualifier_type):
                    return qualifier.value
        return None

    def get_qualifier_values(self, qualifier_type: Type[Qualifier]):
        """
        Returns all Qualifiers of a certain type, or None if qualifier is not present.

        Arguments:
            qualifier_type: one of the following QualifierTypes: [`SetPieceQualifier`][kloppy.domain.models.event.SetPieceQualifier]
                [`BodyPartQualifier`][kloppy.domain.models.event.BodyPartQualifier] [`PassQualifier`][kloppy.domain.models.event.PassQualifier]

        Examples:
            >>> from kloppy.domain import SetPieceQualifier
            >>> pass_event.get_qualifier_values(SetPieceQualifier)
            [<SetPieceType.GOAL_KICK: 'GOAL_KICK'>]
        """
        qualifiers = []
        if self.qualifiers:
            for qualifier in self.qualifiers:
                if isinstance(qualifier, qualifier_type):
                    qualifiers.append(qualifier.value)

        return qualifiers

    def get_related_events(self) -> List["Event"]:
        if not self.dataset:
            raise OrphanedRecordError()

        return [
            self.dataset.get_record_by_id(event_id)
            for event_id in self.related_event_ids
        ]

    def get_related_event(
        self, type_: Union[str, EventType]
    ) -> Optional["Event"]:
        event_type = (
            EventType[type_.upper()] if isinstance(type_, str) else type_
        )
        for related_event in self.get_related_events():
            if related_event.event_type == event_type:
                return related_event
        return None

    """Define all related events for easy access"""

    def related_pass(self) -> Optional["PassEvent"]:
        return self.get_related_event(EventType.PASS)

    def related_shot(self) -> Optional["ShotEvent"]:
        return self.get_related_event(EventType.SHOT)

    def related_take_on(self) -> Optional["TakeOnEvent"]:
        return self.get_related_event(EventType.TAKE_ON)

    def related_carry(self) -> Optional["CarryEvent"]:
        return self.get_related_event(EventType.CARRY)

    def related_substitution(self) -> Optional["SubstitutionEvent"]:
        return self.get_related_event(EventType.SUBSTITUTION)

    def related_card(self) -> Optional["CardEvent"]:
        return self.get_related_event(EventType.CARD)

    def related_player_on(self) -> Optional["PlayerOnEvent"]:
        return self.get_related_event(EventType.PLAYER_ON)

    def related_player_off(self) -> Optional["PlayerOffEvent"]:
        return self.get_related_event(EventType.PLAYER_OFF)

    def related_recovery(self) -> Optional["RecoveryEvent"]:
        return self.get_related_event(EventType.RECOVERY)

    def related_ball_out(self) -> Optional["BallOutEvent"]:
        return self.get_related_event(EventType.BALL_OUT)

    def related_foul_committed(self) -> Optional["FoulCommittedEvent"]:
        return self.get_related_event(EventType.FOUL_COMMITTED)

    def related_formation_change(self) -> Optional["FormationChangeEvent"]:
        return self.get_related_event(EventType.FORMATION_CHANGE)

    def matches(self, filter_) -> bool:
        if filter_ is None:
            return True
        elif callable(filter_):
            return filter_(self)
        elif isinstance(filter_, str):
            """
            Allowed formats:
            1. <event_type>
            2. <event_type>.<result>

            This format always us to go to css selectors without breaking existing code.
            """
            parts = filter_.upper().split(".")
            if len(parts) == 2:
                event_type, result = parts
            elif len(parts) == 1:
                event_type = parts[0]
                result = None
            else:
                raise InvalidFilterError(
                    f"Don't know how to apply filter {filter_}"
                )

            if event_type:
                try:
                    if self.event_type != EventType[event_type]:
                        return False
                except KeyError:
                    raise InvalidFilterError(
                        f"Cannot find event type {event_type}. Possible options: {[e.value.lower() for e in EventType]}"
                    )

            if result:
                if not self.result:
                    return False

                try:
                    if self.result != self.result.__class__[result]:
                        return False
                except KeyError:
                    # result isn't applicable for this event
                    # example: result='GOAL' event=<Pass>
                    return False

            return True

    def __str__(self):
        event_type = (
            self.__class__.__name__
            if not isinstance(self, GenericEvent)
            else f"GenericEvent:{self.event_name}"
        )

        return (
            f"<{event_type} "
            f"event_id='{self.event_id}' "
            f"time='{self.time}' "
            f"player='{self.player}' "
            f"result='{self.result}'>"
        )

    def __repr__(self):
        return str(self)


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class GenericEvent(Event):
    """
    Unrecognised event type.

    By default, all events are deserialized as `GenericEvent` objects.
    Some events may be converted into more specialized event types, such as
    a [`PassEvent`][kloppy.domain.models.event.PassEvent] object.

    Attributes:
        event_type (EventType): `EventType.GENERIC`
        event_name (str): `"generic"`
    """

    event_type: EventType = EventType.GENERIC
    event_name: str = "generic"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class ShotEvent(Event):
    """
    An intentional attempt to score a goal by striking or directing the ball
    towards the opponent's goal. Own goals are always categorized as a shot too.

    Attributes:
        event_type (EventType): `EventType.SHOT`
        event_name (str): `"shot"`
        result (ShotResult): The outcome of the shot.
        result_coordinates (Point): End location of the shot. If a shot is blocked, this is the coordinate of the block. If the shot is saved, it is the coordinate where the keeper touched the ball.
    """

    result: ShotResult
    result_coordinates: Optional[Point] = None

    event_type: EventType = EventType.SHOT
    event_name: str = "shot"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PassEvent(Event):
    """
    The attempted delivery of the ball from one player to another player on the same team.

    Attributes:
        event_type (EventType): `EventType.PASS`
        event_name (str): `"pass"`
        receive_timestamp (Time): The time the pass was received.
        receiver_coordinates (Point): The coordinates where the pass was received.
        receiver_player (Player): The intended receiver of the pass.
        result (PassResult): The pass's outcome.
    """

    receive_timestamp: Time
    receiver_player: Player
    receiver_coordinates: Point

    result: PassResult

    event_type: EventType = EventType.PASS
    event_name: str = "pass"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class TakeOnEvent(Event):
    """
    An attempt by one player to dribble past an opponent.

    Attributes:
        event_type (EventType): `EventType.TAKE_ON`
        event_name (str): `"take_on"`
        result (TakeOnResult): The take-on's outcome.
    """

    result: TakeOnResult

    event_type: EventType = EventType.TAKE_ON
    event_name: str = "take_on"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class CarryEvent(Event):
    """
    A player controls the ball at their feet while moving or standing still.

    Attributes:
        event_type (EventType): `EventType.CARRY`
        event_name (str): `"carry"`
        end_timestamp (Time): Duration of the carry.
        end_coordinates (Point): Coordinate on the pitch where the carry ended.
        result (CarryResult): The carry's outcome.
    """

    end_timestamp: Time
    end_coordinates: Point

    result: CarryResult

    event_type: EventType = EventType.CARRY
    event_name: str = "carry"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class InterceptionEvent(Event):
    """
    When a player intercepts any pass event between opposition players and
    prevents the ball reaching its target.

    Attributes:
        event_type (EventType): `EventType.INTERCEPTION`
        event_name (str): `"interception"`
    """

    event_type: EventType = EventType.INTERCEPTION
    event_name: str = "interception"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class ClearanceEvent(Event):
    """
    A defensive action when a player attempts to get the ball away from
    a dangerous zone on the pitch with no immediate target regarding
    a recipient for the ball.

    Attributes:
        event_type (EventType): `EventType.CLEARANCE`
        event_name (str): `"clearance"`
    """

    event_type: EventType = EventType.CLEARANCE
    event_name: str = "clearance"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class DuelEvent(Event):
    """
    A contest between two players of opposing sides in the match. Duel events
    come in pairs: one for the attacking team, one for the defending team.
    If the duel is a take on, the offensive one has type `TAKE_ON`.

    Attributes:
        event_type (EventType): `EventType.DUEL`
        event_name (str): `"duel"`
    """

    event_type: EventType = EventType.DUEL
    event_name: str = "duel"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class SubstitutionEvent(Event):
    """
    A player is substituted off the field and replaced by another player.

    Attributes:
        event_type (EventType): `EventType.SUBSTITUTION`
        event_name (str): `"substitution"`
        replacement_player (Player): The player coming on the pitch.
    """

    replacement_player: Player
    position: Optional[PositionType] = None

    event_type: EventType = EventType.SUBSTITUTION
    event_name: str = "substitution"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PlayerOffEvent(Event):
    """
    A player goes/is carried out of the pitch without a substitution.

    Attributes:
        event_type (EventType): `EventType.PLAYER_OFF`
        event_name (str): `"player_off"`
    """

    event_type: EventType = EventType.PLAYER_OFF
    event_name: str = "player_off"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PlayerOnEvent(Event):
    """
    A player returns to the pitch after a `PlayerOff` event.

    Attributes:
        event_type (EventType): `EventType.PLAYER_ON`
        event_name (str): `"player_on"`
    """

    event_type: EventType = EventType.PLAYER_ON
    event_name: str = "player_on"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class CardEvent(Event):
    """
    When a player receives a card.

    Attributes:
        event_type (EventType): `EventType.CARD`
        event_name (str): `"card"`
        card_type (CardType): Attribute specifying the card.
    """

    card_type: CardType

    event_type: EventType = EventType.CARD
    event_name: str = "card"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class FormationChangeEvent(Event):
    """
    A team alters its formation

    Attributes:
        event_type (EventType): `EventType.FORMATION_CHANGE`
        event_name (str): `"card"`
        formation_type (FormationType): The new formation being used.
        player_positions (dict[Player, Position], optional): The players and their positions.
    """

    formation_type: FormationType
    player_positions: Optional[Dict[Player, PositionType]] = None

    event_type: EventType = EventType.FORMATION_CHANGE
    event_name: str = "formation_change"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class RecoveryEvent(Event):
    """
    A player gathers a loose ball and gains control of possession for their team.

    Attributes:
        event_type (EventType): `EventType.RECOVERY`
        event_name (str): "recovery"
    """

    event_type: EventType = EventType.RECOVERY
    event_name: str = "recovery"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class BallOutEvent(Event):
    """
    When the ball goes out of bounds.

    Attributes:
        event_type (EventType): `EventType.BALL_OUT`
        event_name (str): "ball_out"
    """

    event_type: EventType = EventType.BALL_OUT
    event_name: str = "ball_out"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class MiscontrolEvent(Event):
    """
    A player unsuccessfully controls the ball and loses possession.

    Attributes:
        event_type (EventType): `EventType.MISCONTROL`
        event_name (str): "miscontrol"
    """

    event_type: EventType = EventType.MISCONTROL
    event_name: str = "miscontrol"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class FoulCommittedEvent(Event):
    """
    Indicates a foul has been committed. The event is defined for the team that
    commits the foul.

    Attributes:
        event_type (EventType): `EventType.FOUL_COMMITTED`
        event_name (str): "foul_committed"
    """

    event_type: EventType = EventType.FOUL_COMMITTED
    event_name: str = "foul_committed"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class GoalkeeperEvent(Event):
    """
    Indicates an action executed by a goalkeeper.

    Attributes:
        event_type (EventType): `EventType.GOALKEEPER`
        event_name (str): "goalkeeper"
    """

    event_type: EventType = EventType.GOALKEEPER
    event_name: str = "goalkeeper"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PressureEvent(Event):
    """
    A player pressures an opponent to force a mistake.

    Attributes:
        event_type (EventType): `EventType.Pressure`
        event_name (str): `"pressure"`
        end_timestamp (Time): When the pressing ended.
    """

    end_timestamp: Time

    event_type: EventType = EventType.PRESSURE
    event_name: str = "pressure"


@dataclass(repr=False)
@docstring_inherit_attributes(Dataset)
class EventDataset(Dataset[Event]):
    """
    An event stream dataset.

    Attributes:
        dataset_type (DatasetType): `"DatasetType.EVENT"`
        events (List[Event]): A list of events. Alias for `records`.
        metadata (Metadata): Metadata for the dataset.
    """

    dataset_type: DatasetType = DatasetType.EVENT

    def _update_formations_and_positions(self):
        """Update team formations and player positions based on Substitution and TacticalShift events."""
        max_leeway = timedelta(seconds=60)

        for event in self.events:
            if isinstance(event, SubstitutionEvent):
                event.replacement_player.set_position(
                    event.time,
                    event.replacement_player.starting_position
                    or event.player.positions.last(default=None),
                )
                event.player.set_position(event.time, None)

            elif isinstance(event, FormationChangeEvent):
                if event.player_positions:
                    for player, position in event.player_positions.items():
                        if len(player.positions.items):
                            last_time, last_position = player.positions.last(
                                include_time=True
                            )
                            if last_position != position:
                                # Only update when the position changed
                                if event.time - last_time < max_leeway:
                                    # Often the formation change is detected a couple of seconds after a Substitution.
                                    # In this case we need to use the time of the Substitution
                                    player.positions.set(last_time, position)
                                else:
                                    player.positions.set(event.time, position)

                if event.team.formations.items:
                    last_time, last_formation = event.team.formations.last(
                        include_time=True
                    )
                    if last_formation != event.formation_type:
                        event.team.formations.set(
                            event.time, event.formation_type
                        )

                elif event.team.starting_formation:
                    if event.team.starting_formation != event.formation_type:
                        event.team.formations.set(
                            event.time, event.formation_type
                        )

                else:
                    event.team.formations.set(event.time, event.formation_type)

    @property
    def events(self):
        return self.records

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        return self.get_record_by_id(event_id)

    def add_state(self, *builder_keys):
        """
        See [`add_state`][kloppy.domain.services.state_builder.add_state]
        """
        from kloppy.domain.services.state_builder import add_state

        return add_state(self, *builder_keys)

    @deprecated(
        "to_pandas will be removed in the future. Please use to_df instead."
    )
    def to_pandas(
        self,
        record_converter: Optional[Callable[[Event], Dict]] = None,
        additional_columns: Optional[
            Dict[str, Union[str, Callable[[Event], Any]]]
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
                DefaultEventTransformer,
            )

            record_converter = DefaultEventTransformer()

        def generic_record_converter(event: Event):
            row = record_converter(event)
            if additional_columns:
                for k, v in additional_columns.items():
                    if callable(v):
                        value = v(event)
                    else:
                        value = v
                    row.update({k: value})
            return row

        return pd.DataFrame.from_records(
            map(generic_record_converter, self.records)
        )

    def aggregate(self, type_: str, **aggregator_kwargs) -> List[Any]:
        if type_ == "minutes_played":
            from kloppy.domain.services.aggregators.minutes_played import (
                MinutesPlayedAggregator,
            )

            aggregator = MinutesPlayedAggregator(**aggregator_kwargs)
        else:
            raise KloppyError(f"No aggregator {type_} not found")

        return aggregator.aggregate(self)


__all__ = [
    "EnumQualifier",
    "ResultType",
    "EventType",
    "ShotResult",
    "PassResult",
    "TakeOnResult",
    "CarryResult",
    "Event",
    "GenericEvent",
    "ShotEvent",
    "PassEvent",
    "TakeOnEvent",
    "CarryEvent",
    "ClearanceEvent",
    "InterceptionEvent",
    "InterceptionResult",
    "SubstitutionEvent",
    "PlayerOnEvent",
    "PlayerOffEvent",
    "CardEvent",
    "CardType",
    "CardQualifier",
    "FormationType",
    "FormationChangeEvent",
    "EventDataset",
    "RecoveryEvent",
    "MiscontrolEvent",
    "FoulCommittedEvent",
    "BallOutEvent",
    "SetPieceType",
    "Qualifier",
    "SetPieceQualifier",
    "PassQualifier",
    "PassType",
    "BodyPart",
    "BodyPartQualifier",
    "GoalkeeperEvent",
    "GoalkeeperQualifier",
    "GoalkeeperAction",
    "GoalkeeperActionType",
    "CounterAttackQualifier",
    "DuelEvent",
    "DuelType",
    "DuelQualifier",
    "DuelResult",
]
