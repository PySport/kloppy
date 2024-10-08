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
    TYPE_CHECKING,
)

from kloppy.domain.models.common import (
    DatasetType,
    AttackingDirection,
    OrientationError,
    Position,
)
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
class Qualifier(ABC):
    value: None

    @abstractmethod
    def to_dict(self):
        """
        Return the qualifier as a dict
        """
        pass

    @property
    def name(self):
        return camelcase_to_snakecase(
            removes_suffix(type(self).__name__, "Qualifier")
        )


@dataclass
class BoolQualifier(Qualifier, ABC):
    value: bool

    def to_dict(self):
        return {f"is_{self.name}": self.value}


class EnumQualifier(Qualifier, ABC):
    value: Enum

    def to_dict(self):
        return {f"{self.name}_type": self.value.value}


class SetPieceType(Enum):
    """
    SetPieceType

    Attributes:
        GOAL_KICK (SetPieceType):
        FREE_KICK (SetPieceType):
        THROW_IN (SetPieceType):
        CORNER_KICK (SetPieceType):
        PENALTY (SetPieceType):
        KICK_OFF (SetPieceType):
    """

    GOAL_KICK = "GOAL_KICK"
    FREE_KICK = "FREE_KICK"
    THROW_IN = "THROW_IN"
    CORNER_KICK = "CORNER_KICK"
    PENALTY = "PENALTY"
    KICK_OFF = "KICK_OFF"


@dataclass
class SetPieceQualifier(EnumQualifier):
    """
    SetPieceQualifier

    Attributes:
        value: Specifies the type of set piece
    """

    value: SetPieceType


@dataclass
class CardQualifier(EnumQualifier):
    """
    CardQualifier

    Attributes:
        value: Specifies the type card
    """

    value: CardType


class PassType(Enum):
    """
    PassType

    Attributes:
        CROSS (PassType):
        HAND_PASS (PassType):
        HEAD_PASS (PassType):
        HIGH_PASS (PassType):
        LAUNCH (PassType):
        SIMPLE_PASS (PassType):
        SMART_PASS (PassType):
        LONG_BALL (PassType)
        THROUGH_BALL (PassType)
        CHIPPED_PASS (PassType)
        FLICK_ON (PassType)
        ASSIST (PassType)
        ASSIST_2ND (PassType)
        SWITCH_OF_PLAY (PassType)
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
class PassQualifier(EnumQualifier):
    value: PassType


class BodyPart(Enum):
    """
    BodyPart

    Attributes:
        RIGHT_FOOT (BodyPart): Pass or Shot with right foot, save with right foot (for goalkeepers).
        LEFT_FOOT (BodyPart): Pass or Shot with left foot, save with left foot (for goalkeepers).
        HEAD (BodyPart): Pass or Shot with head, save with head (for goalkeepers).
        OTHER (BodyPart): Other body part (chest, back, etc.), for Pass and Shot.
        HEAD_OTHER (BodyPart): Pass or Shot with head or other body part. Only used when the
                               data provider does not distinguish between HEAD and OTHER.
        BOTH_HANDS (BodyPart): Goalkeeper only. Save with both hands.
        CHEST (BodyPart): Goalkeeper only. Save with chest.
        LEFT_HAND (BodyPart): Goalkeeper only. Save with left hand.
        RIGHT_HAND (BodyPart): Goalkeeper only. Save with right hand.
        DROP_KICK (BodyPart): Pass is a keeper drop kick.
        KEEPER_ARM (BodyPart): Pass thrown from keepers hands.
        NO_TOUCH (BodyPart): Pass only. A player deliberately let the pass go past him
                             instead of receiving it to deliver to a teammate behind him.
                             (Also known as a "dummy").
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
class BodyPartQualifier(EnumQualifier):
    value: BodyPart


class GoalkeeperAction(Enum):
    """
    Deprecated: GoalkeeperAction has been renamed to GoalkeeperActionType.

    Attributes:
        SAVE (GoalkeeperAction): Goalkeeper faces shot and saves.
        CLAIM (GoalkeeperAction): Goalkeeper catches cross.
        PUNCH (GoalkeeperAction): Goalkeeper punches ball clear.
        PICK_UP (GoalkeeperAction): Goalkeeper picks up ball.
        SMOTHER (GoalkeeperAction): Goalkeeper coming out to dispossess a player,
                                  equivalent to a tackle for an outfield player.
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
        SMOTHER (GoalkeeperActionType): Goalkeeper coming out to dispossess a player,
                                  equivalent to a tackle for an outfield player.
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
class GoalkeeperQualifier(EnumQualifier):
    value: GoalkeeperActionType


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
class DuelQualifier(EnumQualifier):
    value: DuelType


@dataclass
class CounterAttackQualifier(BoolQualifier):
    pass


@dataclass
@docstring_inherit_attributes(DataRecord)
class Event(DataRecord, ABC):
    """
    Abstract event baseclass. All other event classes inherit from this class.

    Attributes:
        event_id: identifier given by provider
        team: See [`Team`][kloppy.domain.models.common.Team]
        player: See [`Player`][kloppy.domain.models.common.Player]
        coordinates: Coordinates where event happened. See [`Point`][kloppy.domain.models.pitch.Point]
        raw_event: Dict
        state: Dict[str, Any]
        qualifiers: See [`Qualifier`][kloppy.domain.models.event.Qualifier]
    """

    event_id: str
    team: Team
    player: Player
    coordinates: Point

    result: Optional[ResultType]

    raw_event: Dict
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
    GenericEvent

    Attributes:
        event_type (EventType): `EventType.GENERIC` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"generic"`
    """

    event_type: EventType = EventType.GENERIC
    event_name: str = "generic"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class ShotEvent(Event):
    """
    ShotEvent

    Attributes:
        event_type (EventType): `EventType.SHOT` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"shot"`,
        result_coordinates (Point): See [`Point`][kloppy.domain.models.pitch.Point]
        result (ShotResult): See [`ShotResult`][kloppy.domain.models.event.ShotResult]
    """

    result: ShotResult
    result_coordinates: Point = None

    event_type: EventType = EventType.SHOT
    event_name: str = "shot"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PassEvent(Event):
    """
    PassEvent

    Attributes:
        event_type (EventType): `EventType.PASS` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"pass"`
        receive_timestamp (float):
        receiver_coordinates (Point): See [`Point`][kloppy.domain.models.pitch.Point]
        receiver_player (Player): See [`Player`][kloppy.domain.models.common.Player]
        result (PassResult): See [`PassResult`][kloppy.domain.models.event.PassResult]
    """

    receive_timestamp: float
    receiver_player: Player
    receiver_coordinates: Point

    result: PassResult

    event_type: EventType = EventType.PASS
    event_name: str = "pass"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class TakeOnEvent(Event):
    """
    TakeOnEvent

    Attributes:
        event_type (EventType): `EventType.TAKE_ON` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"take_on"`,
        result (TakeOnResult): See [`TakeOnResult`][kloppy.domain.models.event.TakeOnResult]
    """

    result: TakeOnResult

    event_type: EventType = EventType.TAKE_ON
    event_name: str = "take_on"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class CarryEvent(Event):
    """
    CarryEvent

    Attributes:
        event_type (EventType): `EventType.CARRY` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"carry"`,
        end_timestamp (float):
        end_coordinates (Point): See [`Point`][kloppy.domain.models.pitch.Point]
        result (CarryResult): See [`CarryResult`][kloppy.domain.models.event.CarryResult]
    """

    end_timestamp: float
    end_coordinates: Point

    result: CarryResult

    event_type: EventType = EventType.CARRY
    event_name: str = "carry"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class InterceptionEvent(Event):
    """
    InterceptionEvent

    Attributes:
        event_type (EventType): `EventType.INTERCEPTION` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"interception"`
    """

    event_type: EventType = EventType.INTERCEPTION
    event_name: str = "interception"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class ClearanceEvent(Event):
    """
    ClearanceEvent

    Attributes:
        event_type (EventType): `EventType.CLEARANCE` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"clearance"`
    """

    event_type: EventType = EventType.CLEARANCE
    event_name: str = "clearance"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class DuelEvent(Event):
    """
    DuelEvent

    Attributes:
        event_type (EventType): `EventType.DUEL` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"duel"`

    """

    event_type: EventType = EventType.DUEL
    event_name: str = "duel"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class SubstitutionEvent(Event):
    """
    SubstitutionEvent

    Attributes:
        event_type (EventType): `EventType.SUBSTITUTION` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"substitution"`,
        replacement_player (Player): See [`Player`][kloppy.domain.models.common.Player]
    """

    replacement_player: Player
    position: Optional[Position] = None

    event_type: EventType = EventType.SUBSTITUTION
    event_name: str = "substitution"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PlayerOffEvent(Event):
    """
    PlayerOffEvent

    Attributes:
        event_type (EventType): `EventType.PLAYER_OFF` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"player_off"`
    """

    event_type: EventType = EventType.PLAYER_OFF
    event_name: str = "player_off"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PlayerOnEvent(Event):
    """
    PlayerOnEvent

    Attributes:
        event_type (EventType): `EventType.PLAYER_ON` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"player_on"`
    """

    event_type: EventType = EventType.PLAYER_ON
    event_name: str = "player_on"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class CardEvent(Event):
    """
    CardEvent

    Attributes:
        event_type (EventType): `EventType.CARD` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"card"`
        card_type: See [`CardType`][kloppy.domain.models.event.CardType]
    """

    card_type: CardType

    event_type: EventType = EventType.CARD
    event_name: str = "card"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class FormationChangeEvent(Event):
    """
    FormationChangeEvent

    Attributes:
        event_type (EventType): `EventType.FORMATION_CHANGE` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"card"`
        formation_type: See [`FormationType`][kloppy.domain.models.formation.FormationType]
    """

    formation_type: FormationType
    player_positions: Optional[Dict[Player, Position]] = None

    event_type: EventType = EventType.FORMATION_CHANGE
    event_name: str = "formation_change"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class RecoveryEvent(Event):
    """
    RecoveryEvent

    Attributes:
        event_type (EventType): `EventType.RECOVERY` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): "recovery"
    """

    event_type: EventType = EventType.RECOVERY
    event_name: str = "recovery"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class BallOutEvent(Event):
    """
    BallOutEvent

    Attributes:
        event_type (EventType): `EventType.BALL_OUT` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): "ball_out"
    """

    event_type: EventType = EventType.BALL_OUT
    event_name: str = "ball_out"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class MiscontrolEvent(Event):
    """
    MiscontrolEvent
    Attributes:
        event_type (EventType): `EventType.MISCONTROL` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): "miscontrol"
    """

    event_type: EventType = EventType.MISCONTROL
    event_name: str = "miscontrol"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class FoulCommittedEvent(Event):
    """
    FoulCommittedEvent

    Attributes:
        event_type (EventType): `EventType.FOUL_COMMITTED` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): "foul_committed"
    """

    event_type: EventType = EventType.FOUL_COMMITTED
    event_name: str = "foul_committed"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class GoalkeeperEvent(Event):
    """
    GoalkeeperEvent

    Attributes:
        event_type (EventType): `EventType.GOALKEEPER` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): "goalkeeper"
    """

    event_type: EventType = EventType.GOALKEEPER
    event_name: str = "goalkeeper"


@dataclass(repr=False)
@docstring_inherit_attributes(Event)
class PressureEvent(Event):
    """
    PressureEvent

    Attributes:
        event_type (EventType): `EventType.Pressure` (See [`EventType`][kloppy.domain.models.event.EventType])
        event_name (str): `"pressure"`,
        end_timestamp (float):
    """

    end_timestamp: float

    event_type: EventType = EventType.PRESSURE
    event_name: str = "pressure"


@dataclass(repr=False)
class EventDataset(Dataset[Event]):
    """
    EventDataset

    Attributes:
        metadata: See [`Metadata`][kloppy.domain.models.common.Metadata]
        records (List[Event]): See [`Event`][kloppy.domain.models.event.Event]
        dataset_type: `DatasetType.EVENT` (See [`DatasetType`][kloppy.domain.models.common.DatasetType])
        events: alias for `records`
    """

    records: List[Event]

    dataset_type: DatasetType = DatasetType.EVENT

    def _update_player_positions(self):
        """Update player positions based on Substitution and TacticalShift events."""
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

    @property
    def events(self):
        return self.records

    def get_event_by_id(self, event_id: str) -> Event:
        return self.get_record_by_id(event_id)

    def add_state(self, *builder_keys):
        """
        See [add_state][kloppy.domain.services.state_builder.add_state]
        """
        from kloppy.domain.services.state_builder import add_state

        return add_state(self, *builder_keys)

    @deprecated(
        "to_pandas will be removed in the future. Please use to_df instead."
    )
    def to_pandas(
        self,
        record_converter: Callable[[Event], Dict] = None,
        additional_columns: Dict[
            str, Union[Callable[[Event], Any], Any]
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
