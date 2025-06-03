from datetime import timedelta
from enum import Enum, EnumMeta
from typing import NamedTuple

from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    CarryResult,
    CounterAttackQualifier,
    DuelQualifier,
    DuelResult,
    DuelType,
    Event,
    EventFactory,
    ExpectedGoals,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    InterceptionResult,
    PassQualifier,
    PassResult,
    PassType,
    PositionType,
    PostShotExpectedGoals,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TakeOnResult,
)
from kloppy.domain.models.event import UnderPressureQualifier
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.pff.helpers import (
    get_period_by_id,
    get_team_by_id,
    parse_coordinates,
    parse_str_ts,
)


position_types_mapping: dict[str, PositionType] = {
    'GK': PositionType.Goalkeeper,  # Provider: Goalkeeper
    'RB': PositionType.RightBack,  # Provider: Right Back
    'RCB': PositionType.RightCenterBack,  # Provider: Right Center Back
    'CB': PositionType.CenterBack,  # Provider: Center Back
    'MCB': PositionType.CenterBack,  # Provider: Mid Center Back
    'LCB': PositionType.LeftCenterBack,  # Provider: Left Center Back
    'LB': PositionType.LeftBack,  # Provider: Left Back
    'LWB': PositionType.LeftWingBack,  # Provider: Left Wing Back
    'RWB': PositionType.RightWingBack,  # Provider: Right Wing Back
    'D': PositionType.Defender,  # Provider: Defender
    'M': PositionType.Midfielder,  # Provider: Midfielder
    'DM': PositionType.DefensiveMidfield,  # Provider: Defensive Midfield
    'RM': PositionType.RightMidfield,  # Provider: Right Midfield
    'CM': PositionType.CenterMidfield,  # Provider: Center Midfield
    'LM': PositionType.LeftMidfield,  # Provider: Left Midfield
    'RW': PositionType.RightWing,  # Provider: Right Wing
    'AM': PositionType.AttackingMidfield,  # Provider: Attacking Midfield
    'LW': PositionType.LeftWing,  # Provider: Left Wing
    'CF': PositionType.Striker,  # Provider: Center Forward (mapped to Striker)
    'F': PositionType.Attacker,  # Provider: Forward (mapped to Attacker)
}


class TypesEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kw):
        if isinstance(value, dict):
            if value["id"] not in cls._value2member_map_:
                raise DeserializationError(
                    "Unknown PFF {}: {}/{}".format(
                        (
                            cls.__qualname__.replace("_", " ")
                            .replace(".", " ")
                            .title()
                        ),
                        value["id"],
                        value["name"],
                    )
                )
            value = cls(value["id"])
        elif value not in cls._value2member_map_:
            raise DeserializationError(
                "Unknown PFF {}: {}".format(
                    (
                        cls.__qualname__.replace("_", " ")
                        .replace(".", " ")
                        .title()
                    ),
                    value,
                )
            )
        return super().__call__(value, *args, **kw)

class END_TYPE(Enum, metaclass=TypesEnumMeta):
    """"The list of end of half types used in PFF data."""

    FIRST_HALF_END = 'FIRST'
    SECOND_HALF_END = 'SECOND'
    THIRD_HALF_END  = 'F'
    FOURTH_HALF_END = 'S'
    GAME_END = 'G'


class EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """The list of game event types used in PFF data."""

    FIRST_HALF_KICKOFF = 'FIRSTKICKOFF'
    SECOND_HALF_KICKOFF = 'SECONDKICKOFF'
    THIRD_HALF_KICKOFF = 'THIRDKICKOFF'
    FOURTH_HALF_KICKOFF = 'FOURTHKICKOFF'
    GAME_CLOCK_OBSERVATION = 'CLK'
    END_OF_HALF = 'END'
    GROUND = 'G'
    PLAYER_OFF = 'OFF'
    PLAYER_ON = 'ON'
    POSSESSION = 'OTB'
    BALL_OUT_OF_PLAY = 'OUT'
    PAUSE_OF_GAME_TIME = 'PAU'
    SUB = 'SUB'
    VIDEO = 'VID'


class POSSESSION_EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """The list of possession event types used in PFF data."""

    BALL_CARRY = 'BC'
    CHALLENGE = 'CH'
    CLEARANCE = 'CL'
    CROSS = 'CR'
    FOUL = 'FO'
    PASS = 'PA'
    REBOUND = 'RE'
    SHOT = 'SH'
    TOUCHES = 'IT'


class BODYPART(Enum, metaclass=TypesEnumMeta):
    """The list of body parts used in PFF data."""

    BACK = 'BA'
    BOTTOM = 'BO'
    TWO_HAND_CATCH = 'CA'
    CHEST = 'CH'
    HEAD = 'HE'
    LEFT_FOOT = 'L'
    LEFT_ARM = 'LA'
    LEFT_BACK_HEEL = 'LB'
    LEFT_SHOULDER = 'LC'
    LEFT_HAND = 'LH'
    LEFT_KNEE = 'LK'
    LEFT_SHIN = 'LS'
    LEFT_THIGH = 'LT'
    TWO_HAND_PALM = 'PA'
    TWO_HAND_PUNCH = 'PU'
    RIGHT_FOOT = 'R'
    RIGHT_ARM = 'RA'
    RIGHT_BACK_HEEL = 'RB'
    RIGHT_SHOULDER = 'RC'
    RIGHT_HAND = 'RH'
    RIGHT_KNEE = 'RK'
    RIGHT_SHIN = 'RS'
    RIGHT_THIGH = 'RT'
    TWO_HANDS = 'TWOHANDS'
    VIDEO_MISSING = 'VM'


class EVENT:
    """Base class for PFF events.

    This class is used to deserialize PFF events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
    """

    def __init__(self, raw_event: dict):
        self.raw_event = raw_event

    def set_refs(self, periods, teams, events):
        self.period = get_period_by_id(self.raw_event["gameEvents"]["period"], periods)
        self.team = get_team_by_id(self.raw_event["gameEvents"]["teamId"], teams)
        self.possession_team = get_team_by_id(
            self.raw_event["gameEvents"]["teamId"], teams
        )
        self.player = (
            self.team.get_player_by_id(self.raw_event["gameEvents"]["playerId"])
            if "player" in self.raw_event
            else None
        )
        self.related_events = [
            events.get(event_id)
            for event_id in events.keys()
            if event_id.split('_')[0] == self.raw_event.get("gameEventId", "")
        ]
        return self

    def deserialize(self, event_factory: EventFactory) -> list[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()

        # create events
        base_events = self._create_events(
            event_factory, **generic_event_kwargs
        )
        # aerial_won_events = self._create_aerial_won_event(
        #     event_factory, **generic_event_kwargs
        # )
        # ball_out_events = self._create_ball_out_event(
        #     event_factory, **generic_event_kwargs
        # )

        # # add qualifiers
        # for event in aerial_won_events + base_events:
        #     self._add_under_pressure_qualifier(event)
        # for event in aerial_won_events + base_events + ball_out_events:
        #     self._add_play_pattern_qualifiers(event)

        # return events (note: order is important)
        return base_events
        # return aerial_won_events + base_events + ball_out_events

    def _parse_generic_kwargs(self) -> dict:
        event_id = (
            self.raw_event["possessionEventId"]
            if self.raw_event["possessionEventId"] is not None
            else self.raw_event["gameEventId"]
        )
        return {
            "period": self.period,
            "timestamp": self.raw_event["eventTime"],
            "ball_owning_team": self.possession_team,
            "ball_state": BallState.ALIVE,
            "event_id": event_id,
            "team": self.team,
            "player": self.player,
            "coordinates": None,
            "raw_event": self.raw_event,
        }

    def _add_under_pressure_qualifier(self, event: Event) -> Event:
        if ("under_pressure" in self.raw_event) and (
            self.raw_event["under_pressure"]
        ):
            q = UnderPressureQualifier(True)
            event.qualifiers = event.qualifiers or []
            event.qualifiers.append(q)

        return event

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> list[Event]:
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["gameEvents"]["gameEventType"],
            **generic_event_kwargs,
        )
        return [generic_event]


def possession_event_decoder(possession_event: dict) -> EVENT:
    type_to_possession_event = {
        POSSESSION_EVENT_TYPE.PASS: EVENT,
        POSSESSION_EVENT_TYPE.SHOT: EVENT,
        POSSESSION_EVENT_TYPE.CROSS: EVENT,
        POSSESSION_EVENT_TYPE.CLEARANCE: EVENT,
        POSSESSION_EVENT_TYPE.BALL_CARRY: EVENT,
        POSSESSION_EVENT_TYPE.CHALLENGE: EVENT,
        POSSESSION_EVENT_TYPE.FOUL: EVENT,
        POSSESSION_EVENT_TYPE.REBOUND: EVENT,
        POSSESSION_EVENT_TYPE.TOUCHES: EVENT,
    }


def event_decoder(raw_event: dict) -> EVENT:
    type_to_event = {
        EVENT_TYPE.POSSESSION: EVENT,
        EVENT_TYPE.GAME_CLOCK_OBSERVATION: EVENT,
        EVENT_TYPE.GROUND: EVENT,
        EVENT_TYPE.BALL_OUT_OF_PLAY: EVENT,
        EVENT_TYPE.SUB: EVENT,
        EVENT_TYPE.PLAYER_ON: EVENT,
        EVENT_TYPE.PLAYER_OFF: EVENT,
    }

    event_type = EVENT_TYPE(raw_event["gameEvents"]["gameEventType"])
    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
