from datetime import timedelta
from enum import Enum, EnumMeta
from typing import Dict, List, NamedTuple, Optional, Union

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
    Point,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.impect.helpers import (
    get_period_by_id,
    get_team_by_id,
    parse_coordinates,
)


class EVENT_TYPE(Enum):
    """The list of event types that compose all of Impect data."""

    PASS = "PASS"
    DRIBBLE = "DRIBBLE"
    SHOT = "SHOT"
    RECEPTION = "RECEPTION"
    LOOSE_BALL_REGAIN = "LOOSE_BALL_REGAIN"
    INTERCEPTION = "INTERCEPTION"
    CLEARANCE = "CLEARANCE"
    GROUND_DUEL = "GROUND_DUEL"
    BLOCK = "BLOCK"
    KICK_OFF = "KICK_OFF"
    THROW_IN = "THROW_IN"
    FREE_KICK = "FREE_KICK"
    GOAL_KICK = "GOAL_KICK"
    CORNER = "CORNER"
    GK_CATCH = "GK_CATCH"
    GK_SAVE = "GK_SAVE"
    GOAL = "GOAL"
    OWN_GOAL = "OWN_GOAL"
    OUT = "OUT"
    OFFSIDE = "OFFSIDE"
    FOUL = "FOUL"
    FINAL_WHISTLE = "FINAL_WHISTLE"
    REFEREE_INTERCEPTION = "REFEREE_INTERCEPTION"
    NO_VIDEO = "NO_VIDEO"
    RED_CARD = "RED_CARD"


class BODYPART(Enum):
    """The list of body parts used in StatsBomb data."""

    FOOT_RIGHT = "FOOT_RIGHT"
    FOOT_LEFT = "FOOT_LEFT"
    BODY = "BODY"
    HEAD = "HEAD"
    HAND = "HAND"


class EVENT:
    """Base class for Impect events.

    This class is used to deserialize Impect events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
    """

    def __init__(self, raw_event: Dict):
        self.raw_event = raw_event

    def set_refs(self, periods, teams, events):
        self.period = get_period_by_id(self.raw_event["periodId"], periods)
        self.team = (
            get_team_by_id(self.raw_event["squadId"], teams)
            if self.raw_event["squadId"]
            else None
        )
        self.possession_team = (
            get_team_by_id(self.raw_event["currentAttackingSquadId"], teams)
            if self.raw_event["currentAttackingSquadId"]
            else None
        )
        self.player = (
            self.team.get_player_by_id(self.raw_event["player"]["id"])
            if self.raw_event["player"]
            else None
        )

        return self

    def deserialize(self, event_factory: EventFactory) -> List[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.
            periods: The periods in the match.
            teams: The teams in the match.
            events: All events in the match.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()
        events = self._create_events(event_factory, **generic_event_kwargs)

        return events

    def _parse_generic_kwargs(self) -> Dict:
        return {
            "period": self.period,
            "timestamp": self.raw_event["gameTime"]["gameTimeInSec"],
            "ball_owning_team": self.possession_team,
            "ball_state": BallState.ALIVE,
            "event_id": self.raw_event["id"],
            "team": self.team,
            "player": self.player,
            "coordinates": parse_coordinates(
                self.raw_event["start"]["adjCoordinates"]
            )
            if self.raw_event["start"]
            else None,
            "related_event_ids": self.raw_event.get("related_events", []),
            "raw_event": self.raw_event,
        }

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["actionType"],
            **generic_event_kwargs,
        )
        return [generic_event]


class PASS(EVENT):
    """Impect Pass event."""

    class ACTION(Enum):
        LOW_PASS = "LOW_PASS"
        LOW_CROSS = "LOW_CROSS"
        HIGH_CROSS = "HIGH_CROSS"
        DIAGONAL_PASS = "DIAGONAL_PASS"
        CHIPPED_PASS = "CHIPPED_PASS"
        SHORT_AERIAL_PASS = "SHORT_AERIAL_PASS"
        HEADER = "HEADER"

    class RESULT(Enum):
        FAIL = "FAIL"
        SUCCESS = "SUCCESS"

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        team = generic_event_kwargs["team"]
        timestamp = timedelta(seconds=generic_event_kwargs["timestamp"])
        pass_dict = self.raw_event["pass"]

        result = (
            PassResult.COMPLETE
            if self.raw_event["result"] == "SUCCESS"
            else PassResult.INCOMPLETE
        )
        receiver_info = pass_dict["receiver"]
        if receiver_info and receiver_info["type"] == "TEAMMATE":
            receiver_player = team.get_player_by_id(receiver_info["playerId"])
        else:
            receiver_player = None
        end_coordinates_info = self.raw_event["end"]
        if end_coordinates_info:
            receiver_coordinates = parse_coordinates(
                end_coordinates_info["adjCoordinates"]
            )
        else:
            receiver_coordinates = None
        duration = (
            self.raw_event["duration"] if self.raw_event["duration"] else 0
        )
        receive_timestamp = timestamp + timedelta(seconds=duration)

        body_part = BODYPART(self.raw_event["bodyPartExtended"])
        action = self.ACTION(self.raw_event["action"])

        qualifiers = _get_pass_qualifiers(
            action, body_part
        ) + _get_body_part_qualifiers(body_part)

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [pass_event]


def _get_body_part_qualifiers(
    body_part: BODYPART,
) -> List[BodyPartQualifier]:
    impect_to_kloppy_body_part_mapping = {
        BODYPART.FOOT_LEFT: BodyPart.LEFT_FOOT,
        BODYPART.FOOT_RIGHT: BodyPart.RIGHT_FOOT,
        BODYPART.HEAD: BodyPart.HEAD,
        BODYPART.BODY: BodyPart.OTHER,
        BODYPART.HAND: BodyPart.KEEPER_ARM,
    }

    return [
        BodyPartQualifier(value=impect_to_kloppy_body_part_mapping[body_part])
    ]


def _get_pass_qualifiers(action, body_part) -> List[PassQualifier]:
    action_qualifier_mapping = {
        PASS.ACTION.LOW_CROSS: [PassType.CROSS],
        PASS.ACTION.HIGH_CROSS: [PassType.CROSS, PassType.HIGH_PASS],
        PASS.ACTION.SHORT_AERIAL_PASS: [PassType.CHIPPED_PASS],
        PASS.ACTION.CHIPPED_PASS: [PassType.CHIPPED_PASS],
    }
    body_part_qualifier_mapping = {
        BODYPART.HEAD: [PassType.HEAD_PASS],
        BODYPART.HAND: [PassType.HAND_PASS],
    }

    action_qualifier_values = action_qualifier_mapping.get(action, [])
    body_part_qualifier_value = body_part_qualifier_mapping.get(body_part, [])
    qualifier_values = action_qualifier_values + body_part_qualifier_value

    qualifiers = [PassQualifier(value=value) for value in qualifier_values]

    return qualifiers


def create_impect_events(
    raw_events: List[Dict],
) -> Dict[str, Union[EVENT, Dict]]:
    impect_events = {}
    for raw_event in raw_events:
        impect_events[raw_event["id"]] = event_decoder(raw_event)

    return impect_events


def event_decoder(raw_event: Dict) -> Union[EVENT, Dict]:
    type_to_event = {
        EVENT_TYPE.PASS: PASS,
    }
    event_type = EVENT_TYPE(raw_event["actionType"])
    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
