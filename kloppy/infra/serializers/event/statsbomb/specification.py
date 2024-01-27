from datetime import timedelta
from enum import Enum, EnumMeta
from typing import List, Dict, Optional, NamedTuple, Union

from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    CarryResult,
    DuelQualifier,
    DuelResult,
    DuelType,
    Event,
    EventFactory,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    InterceptionResult,
    PassQualifier,
    PassResult,
    PassType,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TakeOnResult,
    FormationType,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.statsbomb.helpers import (
    parse_str_ts,
    get_team_by_id,
    get_period_by_id,
    parse_coordinates,
)


class Version(NamedTuple):
    """StatsBomb data version.

    StatsBomb maintains two levels of accuracy for coordinates in their data.
    This level can differ between Shot events and all other events.


    Attributes:
        shot_fidelity_version: The level of accuracy for Shot events and
            events paired with Shot events (these are Goal Keeper events, Block
            events, Duel events and Freeze Frame objects).
            - In V1, the x-coordinates, y-coordinates and, where appropriate,
              z-coordinates are detailed to a yard with the exception of the
              y-coordinates and z-coordinates in the goal frame of the end
              locations of Shot events.
            - In V2, the x-coordinates, y-coordinates and, where appropriate,
              z-coordinates are detailed to a tenth of a yard.
        xy_fidelity_version: The level of accuracy for all other events.
            - In V1, the x-coordinates and y-coordinates of all the locations
              associated with events are detailed to a yard.
            - In V2, the x-coordinates and y-coordinates of all the locations
              associated with events are detailed to a tenth of a yard.
    """

    shot_fidelity_version: int
    xy_fidelity_version: int


FORMATIONS = {
    3142: FormationType.THREE_ONE_FOUR_TWO,
    312112: FormationType.THREE_ONE_TWO_ONE_ONE_TWO,
    31222: FormationType.THREE_ONE_TWO_TWO_TWO,
    32122: FormationType.THREE_TWO_ONE_TWO_TWO,
    32212: FormationType.THREE_TWO_TWO_ONE_TWO,
    32221: FormationType.THREE_TWO_TWO_TWO_ONE,
    3232: FormationType.THREE_TWO_THREE_TWO,
    3322: FormationType.THREE_THREE_TWO_TWO,
    3412: FormationType.THREE_FOUR_ONE_TWO,
    3421: FormationType.THREE_FOUR_TWO_ONE,
    343: FormationType.THREE_FOUR_THREE,
    3511: FormationType.THREE_FIVE_ONE_ONE,
    352: FormationType.THREE_FIVE_TWO,
    41131: FormationType.FOUR_ONE_ONE_THREE_ONE,
    41212: FormationType.FOUR_ONE_TWO_ONE_TWO,
    41221: FormationType.FOUR_ONE_TWO_TWO_ONE,
    4132: FormationType.FOUR_ONE_THREE_TWO,
    4141: FormationType.FOUR_ONE_FOUR_ONE,
    42121: FormationType.FOUR_TWO_ONE_TWO_ONE,
    4213: FormationType.FOUR_TWO_ONE_THREE,
    42211: FormationType.FOUR_TWO_TWO_ONE_ONE,
    4222: FormationType.FOUR_TWO_TWO_TWO,
    4231: FormationType.FOUR_TWO_THREE_ONE,
    4312: FormationType.FOUR_THREE_ONE_TWO,
    4321: FormationType.FOUR_THREE_TWO_ONE,
    433: FormationType.FOUR_THREE_THREE,
    4411: FormationType.FOUR_FOUR_ONE_ONE,
    442: FormationType.FOUR_FOUR_TWO,
    451: FormationType.FOUR_FIVE_ONE,
    5221: FormationType.FIVE_TWO_TWO_ONE,
    532: FormationType.FIVE_THREE_TWO,
    541: FormationType.FIVE_FOUR_ONE,
}


class TypesEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kw):
        if isinstance(value, dict):
            if value["id"] not in cls._value2member_map_:
                raise DeserializationError(
                    "Unknown StatsBomb {}: {}/{}".format(
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
                "Unknown StatsBomb {}: {}".format(
                    (
                        cls.__qualname__.replace("_", " ")
                        .replace(".", " ")
                        .title()
                    ),
                    value,
                )
            )
        return super().__call__(value, *args, **kw)


class EVENT_TYPE(Enum, metaclass=TypesEnumMeta):
    """The list of event types that compose all of StatsBomb data."""

    FIFTY_FIFTY = 33
    BAD_BEHAVIOUR = 24
    BALL_RECEIPT = 42
    BALL_RECOVERY = 2
    BLOCK = 6
    CAMERA_ON = 5
    CAMERA_OFF = 29
    CARRY = 43
    CLEARANCE = 9
    DISPOSSESSED = 3
    DRIBBLE = 14
    DRIBBLED_PAST = 39
    DUEL = 4
    ERROR = 37
    FOUL_COMMITTED = 22
    FOUL_WON = 21
    GOALKEEPER = 23
    HALF_END = 34
    HALF_START = 18
    INJURY_STOPPAGE = 40
    INTERCEPTION = 10
    MISCONTROL = 38
    OFFSIDE = 8
    OWN_GOAL_AGAINST = 20
    OWN_GOAL_FOR = 25
    PASS = 30
    PLAYER_OFF = 27
    PLAYER_ON = 26
    PRESSURE = 17
    REFEREE_BALL_DROP = 41
    SHIELD = 28
    SHOT = 16
    STARTING_XI = 35
    SUBSTITUTION = 19
    TACTICAL_SHIFT = 36


class BODYPART(Enum, metaclass=TypesEnumMeta):
    """The list of body parts used in StatsBomb data."""

    BOTH_HANDS = 35
    CHEST = 36
    HEAD = 37
    LEFT_FOOT = 38
    LEFT_HAND = 39
    RIGHT_FOOT = 40
    RIGHT_HAND = 41
    DROP_KICK = 68
    KEEPER_ARM = 69
    OTHER = 70
    NO_TOUCH = 106


class EVENT:
    """Base class for StatsBomb events.

    This class is used to deserialize StatsBomb events into kloppy events.
    This default implementation is used for all events that do not have a
    specific implementation. They are deserialized into a generic event.

    Args:
        raw_event: The raw JSON event.
        data_version: The version of the StatsBomb data.
    """

    def __init__(self, raw_event: Dict):
        self.raw_event = raw_event

    def set_version(self, data_version: Version):
        self.fidelity_version = data_version.xy_fidelity_version
        return self

    def set_refs(self, periods, teams, events):
        self.period = get_period_by_id(self.raw_event["period"], periods)
        self.team = get_team_by_id(self.raw_event["team"]["id"], teams)
        self.possession_team = get_team_by_id(
            self.raw_event["possession_team"]["id"], teams
        )
        self.player = (
            self.team.get_player_by_id(self.raw_event["player"]["id"])
            if "player" in self.raw_event
            else None
        )
        self.related_events = [
            events.get(event_id)
            for event_id in self.raw_event.get("related_events", [])
        ]
        return self

    def deserialize(self, event_factory: EventFactory) -> List[Event]:
        """Deserialize the event.

        Args:
            event_factory: The event factory to use to build the event.
            periods: The periods in the match.
            teams: The teams in the match.
            events: All events in the match.
            data_version: The x/y and shot fidelity versions of the data.

        Returns:
            A list of kloppy events.
        """
        generic_event_kwargs = self._parse_generic_kwargs()
        return (
            self._create_aerial_won_event(
                event_factory, **generic_event_kwargs
            )
            + self._create_events(event_factory, **generic_event_kwargs)
            + self._create_ball_out_event(
                event_factory, **generic_event_kwargs
            )
        )

    def _parse_generic_kwargs(self) -> Dict:
        return {
            "period": self.period,
            "timestamp": parse_str_ts(self.raw_event["timestamp"]),
            "ball_owning_team": self.possession_team,
            "ball_state": BallState.ALIVE,
            "event_id": self.raw_event["id"],
            "team": self.team,
            "player": self.player,
            "coordinates": (
                parse_coordinates(
                    self.raw_event["location"],
                    self.fidelity_version,
                )
                if "location" in self.raw_event
                else None
            ),
            "related_event_ids": self.raw_event.get("related_events", []),
            "raw_event": self.raw_event,
        }

    def _create_aerial_won_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        """Add possible aerial won - Applicable to multiple event types"""
        for type_name in ["shot", "clearance", "miscontrol", "pass"]:
            if (
                type_name in self.raw_event
                and "aerial_won" in self.raw_event[type_name]
            ):
                generic_event_kwargs[
                    "event_id"
                ] = f"duel-{generic_event_kwargs['event_id']}"
                duel_qualifiers = [
                    DuelQualifier(value=DuelType.LOOSE_BALL),
                    DuelQualifier(value=DuelType.AERIAL),
                ]
                duel_event = event_factory.build_duel(
                    result=DuelResult.WON,
                    qualifiers=duel_qualifiers,
                    **generic_event_kwargs,
                )
                return [duel_event]
        return []

    def _create_ball_out_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        if self.raw_event.get("out", False):
            generic_event_kwargs[
                "event_id"
            ] = f"out-{generic_event_kwargs['event_id']}"
            generic_event_kwargs["ball_state"] = BallState.DEAD
            ball_out_event = event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [ball_out_event]
        return []

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["type"]["name"],
            **generic_event_kwargs,
        )
        return [generic_event]


class PASS(EVENT):
    """StatsBomb 30/Pass event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        ONE_TOUCH_INTERCEPTION = 64
        RECOVERY = 66
        CORNER_KICK = 61
        FREE_KICK = 62
        GOAL_KICK = 63
        KICK_OFF = 65
        THROW_IN = 67

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        COMPLETE = 8
        INCOMPLETE = 9
        INJURY_CLEARANCE = 74
        OUT = 75
        OFFSIDE = 76
        UNKNOWN = 77

    class HEIGHT(Enum, metaclass=TypesEnumMeta):
        GROUND = 1
        LOW = 2
        HIGH = 3

    class TECHNIQUE(Enum, metaclass=TypesEnumMeta):
        THROUGH_BALL = 108
        INSWINGING = 104
        OUTSWINGING = 105
        STRAIGHT = 107

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        team = generic_event_kwargs["team"]
        timestamp = generic_event_kwargs["timestamp"]
        pass_dict = self.raw_event["pass"]

        result = None
        receiver_player = None
        receiver_coordinates = parse_coordinates(
            pass_dict["end_location"],
            self.fidelity_version,
        )
        receive_timestamp = timestamp + timedelta(
            seconds=self.raw_event.get("duration", 0.0)
        )

        if "outcome" in pass_dict:
            outcome_id = pass_dict["outcome"]["id"]
            outcome_mapping = {
                PASS.OUTCOME.OUT: PassResult.OUT,
                PASS.OUTCOME.INCOMPLETE: PassResult.INCOMPLETE,
                PASS.OUTCOME.OFFSIDE: PassResult.OFFSIDE,
                PASS.OUTCOME.INJURY_CLEARANCE: PassResult.OUT,
                PASS.OUTCOME.UNKNOWN: None,
            }
            result = outcome_mapping.get(PASS.OUTCOME(outcome_id))
        else:
            result = PassResult.COMPLETE
            receiver_player = team.get_player_by_id(
                pass_dict["recipient"]["id"]
            )

        qualifiers = (
            _get_pass_qualifiers(pass_dict)
            + _get_set_piece_qualifiers(EVENT_TYPE.PASS, pass_dict)
            + _get_body_part_qualifiers(pass_dict)
        )

        pass_event = event_factory.build_pass(
            result=result,
            receive_timestamp=receive_timestamp,
            receiver_coordinates=receiver_coordinates,
            receiver_player=receiver_player,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        # if pass is an interception, insert interception prior to pass event
        if "type" in pass_dict:
            generic_event_kwargs[
                "event_id"
            ] = f"interception-{generic_event_kwargs['event_id']}"
            type_id = PASS.TYPE(pass_dict["type"]["id"])
            if type_id == PASS.TYPE.ONE_TOUCH_INTERCEPTION:
                interception_event = event_factory.build_interception(
                    **generic_event_kwargs,
                    result=InterceptionResult.SUCCESS,
                    qualifiers=None,
                )
                return [interception_event, pass_event]

        return [pass_event]

    def _create_ball_out_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        pass_dict = self.raw_event["pass"]
        if (
            self.raw_event.get("out", False)
            or "outcome" in pass_dict
            and PASS.OUTCOME(pass_dict["outcome"]) == PASS.OUTCOME.OUT
        ):
            generic_event_kwargs[
                "event_id"
            ] = f"out-{generic_event_kwargs['event_id']}"
            generic_event_kwargs["ball_state"] = BallState.DEAD
            generic_event_kwargs["coordinates"] = parse_coordinates(
                pass_dict["end_location"],
                self.fidelity_version,
            )

            ball_out_event = event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [ball_out_event]
        return []


class SHOT(EVENT):
    """StatsBomb 16/Shot event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        OPEN_PLAY = 87
        FREE_KICK = 62
        KICK_OFF = 65
        CORNER_KICK = 61
        PENALTY = 88

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        BLOCKED = 96
        GOAL = 97
        OFF_TARGET = 98
        POST = 99
        SAVED = 100
        OFF_WAYWARD = 101
        SAVED_OFF_TARGET = 115
        SAVED_TO_POST = 116

    def set_version(self, data_version: Version):
        self.fidelity_version = data_version.shot_fidelity_version
        return self

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        shot_dict = self.raw_event["shot"]

        outcome_id = SHOT.OUTCOME(shot_dict["outcome"]["id"])

        outcome_mapping = {
            SHOT.OUTCOME.OFF_TARGET: ShotResult.OFF_TARGET,
            SHOT.OUTCOME.SAVED: ShotResult.SAVED,
            SHOT.OUTCOME.SAVED_OFF_TARGET: ShotResult.SAVED,
            SHOT.OUTCOME.SAVED_TO_POST: ShotResult.SAVED,
            SHOT.OUTCOME.POST: ShotResult.POST,
            SHOT.OUTCOME.OFF_WAYWARD: ShotResult.OFF_TARGET,
            SHOT.OUTCOME.BLOCKED: ShotResult.BLOCKED,
            SHOT.OUTCOME.GOAL: ShotResult.GOAL,
        }

        result = outcome_mapping.get(outcome_id)

        if result is None:
            raise DeserializationError(f"Unknown shot outcome: {outcome_id}")

        qualifiers = _get_set_piece_qualifiers(
            EVENT_TYPE.SHOT, shot_dict
        ) + _get_body_part_qualifiers(shot_dict)

        shot_event = event_factory.build_shot(
            result=result,
            qualifiers=qualifiers,
            result_coordinates=parse_coordinates(
                shot_dict["end_location"],
                self.fidelity_version,
            ),
            **generic_event_kwargs,
        )

        return [shot_event]

    def _create_ball_out_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        shot_dict = self.raw_event["shot"]
        if (
            self.raw_event.get("out", False)
            or "outcome" in shot_dict
            and SHOT.OUTCOME(shot_dict["outcome"]) == SHOT.OUTCOME.OFF_TARGET
        ):
            generic_event_kwargs[
                "event_id"
            ] = f"out-{generic_event_kwargs['event_id']}"
            generic_event_kwargs["ball_state"] = BallState.DEAD
            generic_event_kwargs["coordinates"] = parse_coordinates(
                shot_dict["end_location"],
                self.fidelity_version,
            )

            ball_out_event = event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [ball_out_event]
        return []


class INTERCEPTION(EVENT):
    """StatsBomb 10/Interception event."""

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        LOST = 1
        WON = 4
        LOST_IN_PLAY = 13
        LOST_OUT = 14
        SUCCESS = 15
        SUCCESS_IN_PLAY = 16
        SUCCESS_OUT = 17

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        interception_dict = self.raw_event.get("interception", {})

        outcome = interception_dict.get("outcome", {})
        outcome_id = INTERCEPTION.OUTCOME(outcome)
        if outcome_id in [
            INTERCEPTION.OUTCOME.LOST_OUT,
            INTERCEPTION.OUTCOME.SUCCESS_OUT,
        ]:
            result = InterceptionResult.OUT
        elif outcome_id in [
            INTERCEPTION.OUTCOME.WON,
            INTERCEPTION.OUTCOME.SUCCESS,
            INTERCEPTION.OUTCOME.SUCCESS_IN_PLAY,
        ]:
            result = InterceptionResult.SUCCESS
        elif outcome_id in [
            INTERCEPTION.OUTCOME.LOST,
            INTERCEPTION.OUTCOME.LOST_IN_PLAY,
        ]:
            result = InterceptionResult.LOST
        else:
            raise DeserializationError(
                f"Unknown interception outcome: {outcome.get('name')}({outcome_id})"
            )

        interception_event = event_factory.build_interception(
            result=result,
            qualifiers=None,
            **generic_event_kwargs,
        )

        return [interception_event]

    def _create_ball_out_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        interception_dict = self.raw_event.get("interception", {})
        if (
            self.raw_event.get("out", False)
            or "outcome" in interception_dict
            and INTERCEPTION.OUTCOME(interception_dict["outcome"])
            in [
                INTERCEPTION.OUTCOME.LOST_OUT,
                INTERCEPTION.OUTCOME.SUCCESS_OUT,
            ]
        ):
            generic_event_kwargs[
                "event_id"
            ] = f"out-{generic_event_kwargs['event_id']}"
            generic_event_kwargs["ball_state"] = BallState.DEAD
            ball_out_event = event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [ball_out_event]
        return []


class OWN_GOAL_AGAINST(EVENT):
    """StatsBomb 20/Own goal against event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        shot_event = event_factory.build_shot(
            result=ShotResult.OWN_GOAL,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [shot_event]


class OWN_GOAL_FOR(EVENT):
    """StatsBomb 25/Own goal for event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        return []


class CLEARANCE(EVENT):
    """StatsBomb 9/Clearance event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        clearance_dict = self.raw_event.get("clearance", {})
        # Old versions of the data (< v1.1) don't define extra attributes for clearances
        qualifiers = _get_body_part_qualifiers(clearance_dict)

        clearance_event = event_factory.build_clearance(
            result=None,
            qualifiers=qualifiers,
            **generic_event_kwargs,
        )

        return [clearance_event]


class MISCONTROL(EVENT):
    """StatsBomb 38/Miscontrol event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        miscontrol_event = event_factory.build_miscontrol(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )

        return [miscontrol_event]


class DRIBBLE(EVENT):
    """StatsBomb 14/Dribble event."""

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        COMPLETE = 8
        INCOMPLETE = 9

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        dribble_dict = self.raw_event.get("dribble", {})
        result_mapping = {
            DRIBBLE.OUTCOME.INCOMPLETE: TakeOnResult.INCOMPLETE,
            DRIBBLE.OUTCOME.COMPLETE: TakeOnResult.COMPLETE,
        }

        result = TakeOnResult.COMPLETE
        if "outcome" in dribble_dict:
            outcome_id = DRIBBLE.OUTCOME(dribble_dict["outcome"])
            result = result_mapping[outcome_id]

        if result == TakeOnResult.INCOMPLETE:
            for related_event in self.related_events:
                if isinstance(related_event, DUEL):
                    duel_dict = related_event.raw_event.get("duel", {})
                    if "outcome" in duel_dict and DUEL.OUTCOME(
                        duel_dict["outcome"]
                    ) in [DUEL.OUTCOME.SUCCESS_OUT, DUEL.OUTCOME.LOST_OUT]:
                        result = TakeOnResult.OUT
                        break

        take_on_event = event_factory.build_take_on(
            qualifiers=None,
            result=result,
            **generic_event_kwargs,
        )
        return [take_on_event]


class CARRY(EVENT):
    """StatsBomb 43/Carry event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        timestamp = generic_event_kwargs["timestamp"]
        carry_dict = self.raw_event["carry"]
        carry_event = event_factory.build_carry(
            qualifiers=None,
            end_timestamp=timestamp
            + timedelta(seconds=self.raw_event.get("duration", 0)),
            result=CarryResult.COMPLETE,
            end_coordinates=parse_coordinates(
                carry_dict["end_location"],
                self.fidelity_version,
            ),
            **generic_event_kwargs,
        )
        return [carry_event]


class DUEL(EVENT):
    """StatsBomb 4/Duel event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        AERIAL_LOST = 10
        TACKLE = 11

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        # Recorded when DUEL.TYPE is DUEL_TACKLE
        WON = 4
        LOST_IN_PLAY = 13
        LOST_OUT = 14
        SUCCESS = 15
        SUCCESS_IN_PLAY = 16
        SUCCESS_OUT = 17

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        duel_dict = self.raw_event.get("duel", {})

        # Get duel qualifiers
        type_id = DUEL.TYPE(duel_dict["type"])
        duel_qualifiers = []
        if type_id == DUEL.TYPE.AERIAL_LOST:
            duel_qualifiers = [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=DuelType.AERIAL),
            ]
        elif type_id == DUEL.TYPE.TACKLE:
            duel_qualifiers = [DuelQualifier(value=DuelType.GROUND)]

        # Get duel result
        duel_won_outcomes = [
            DUEL.OUTCOME.WON,
            DUEL.OUTCOME.SUCCESS,
            DUEL.OUTCOME.SUCCESS_IN_PLAY,
            DUEL.OUTCOME.SUCCESS_OUT,
        ]
        result = (
            DuelResult.WON
            if type_id != DUEL.TYPE.AERIAL_LOST
            and DUEL.OUTCOME(duel_dict.get("outcome", {})) in duel_won_outcomes
            else DuelResult.LOST
        )

        duel_event = event_factory.build_duel(
            result=result,
            qualifiers=duel_qualifiers,
            **generic_event_kwargs,
        )
        return [duel_event]

    def _create_ball_out_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        duel_dict = self.raw_event.get("duel", {})
        if (
            self.raw_event.get("out", False)
            or "outcome" in duel_dict
            and DUEL.OUTCOME(duel_dict["outcome"])
            in [DUEL.OUTCOME.LOST_OUT, DUEL.OUTCOME.SUCCESS_OUT]
        ):
            generic_event_kwargs[
                "event_id"
            ] = f"out-{generic_event_kwargs['event_id']}"
            generic_event_kwargs["ball_state"] = BallState.DEAD
            ball_out_event = event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [ball_out_event]
        return []


class FIFTY_FIFTY(EVENT):
    """StatsBomb 33/Fifty-Fifty event."""

    class OUTCOME(Enum, metaclass=TypesEnumMeta):
        WON = 4
        LOST = 1
        SUCCESS_TO_TEAM = 3
        SUCCESS_TO_OPPONENT = 2

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        duel_dict = self.raw_event.get("50_50", {})

        # Get duel qualifiers
        duel_qualifiers = [
            DuelQualifier(value=DuelType.LOOSE_BALL),
            DuelQualifier(value=DuelType.GROUND),
        ]

        # Get duel result
        duel_won_outcomes = [
            FIFTY_FIFTY.OUTCOME.WON,
            FIFTY_FIFTY.OUTCOME.SUCCESS_TO_TEAM,
        ]
        result = (
            DuelResult.WON
            if FIFTY_FIFTY.OUTCOME(duel_dict.get("outcome", {}))
            in duel_won_outcomes
            else DuelResult.LOST
        )

        duel_event = event_factory.build_duel(
            result=result,
            qualifiers=duel_qualifiers,
            **generic_event_kwargs,
        )
        return [duel_event]


class GOALKEEPER(EVENT):
    """StatsBomb 23/Goalkeeper event."""

    class TYPE(Enum, metaclass=TypesEnumMeta):
        COLLECTED = 25
        GOAL_CONCEDED = 26
        KEEPER_SWEEPER = 27
        PENALTY_CONCEDED = 28
        PENALTY_SAVED = 29
        PUNCH = 30
        PENALTY_SAVED_TO_POST = 109
        SAVE = 31
        SAVED_TO_POST = 110  # A save by the goalkeeper that hits the post
        SHOT_FACED = 32
        SHOT_SAVED = 33
        SHOT_SAVED_OFF_TARGET = 113
        SHOT_SAVED_TO_POST = (
            114  # A shot saved by the goalkeeper that hits the post
        )
        SMOTHER = 34

    class KEEPER_SWEEPER:
        class OUTCOME(Enum, metaclass=TypesEnumMeta):
            CLAIM = 47
            CLEAR = 48
            WON = 4
            SUCCESS = 15

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        goalkeeper_dict = self.raw_event["goalkeeper"]
        generic_event_kwargs = self._parse_generic_kwargs()

        # parse body part
        body_part_qualifiers = _get_body_part_qualifiers(goalkeeper_dict)
        hands_used = any(
            q.value
            in [
                BodyPart.LEFT_HAND,
                BodyPart.RIGHT_HAND,
                BodyPart.BOTH_HANDS,
            ]
            for q in body_part_qualifiers
        )
        head_or_foot_used = any(
            q.value
            in [
                BodyPart.LEFT_FOOT,
                BodyPart.RIGHT_FOOT,
                BodyPart.HEAD,
            ]
            for q in body_part_qualifiers
        )
        bodypart_missing = len(body_part_qualifiers) == 0

        # parse action type qualifiers
        save_event_types = [
            GOALKEEPER.TYPE.SHOT_SAVED,
            GOALKEEPER.TYPE.PENALTY_SAVED_TO_POST,
            GOALKEEPER.TYPE.SAVED_TO_POST,
            GOALKEEPER.TYPE.SHOT_SAVED_OFF_TARGET,
            GOALKEEPER.TYPE.SHOT_SAVED_TO_POST,
        ]
        type_id = GOALKEEPER.TYPE(goalkeeper_dict.get("type", {}).get("id"))
        outcome_id = goalkeeper_dict.get("outcome", {}).get("id")
        qualifiers = []
        if type_id in save_event_types:
            qualifiers.append(
                GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)
            )
        elif type_id == GOALKEEPER.TYPE.SMOTHER:
            qualifiers.append(
                GoalkeeperQualifier(value=GoalkeeperActionType.SMOTHER)
            )
        elif type_id == GOALKEEPER.TYPE.PUNCH:
            qualifiers.append(
                GoalkeeperQualifier(value=GoalkeeperActionType.PUNCH)
            )
        elif type_id == GOALKEEPER.TYPE.COLLECTED:
            qualifiers.append(
                GoalkeeperQualifier(value=GoalkeeperActionType.CLAIM)
            )
        elif type_id == GOALKEEPER.TYPE.KEEPER_SWEEPER:
            outcome_id = GOALKEEPER.KEEPER_SWEEPER.OUTCOME(
                goalkeeper_dict.get("outcome", {}).get("id")
            )
            if outcome_id == GOALKEEPER.KEEPER_SWEEPER.OUTCOME.CLAIM:
                # a goalkeeper can only pick up the ball with his hands
                if hands_used or bodypart_missing:
                    qualifiers.append(
                        GoalkeeperQualifier(value=GoalkeeperActionType.PICK_UP)
                    )
                # otherwise it's a recovery
                else:
                    recovery = event_factory.build_recovery(
                        result=None,
                        qualifiers=body_part_qualifiers,
                        **generic_event_kwargs,
                    )
                    return [recovery]
            elif outcome_id in [
                GOALKEEPER.KEEPER_SWEEPER.OUTCOME.CLEAR,
                GOALKEEPER.KEEPER_SWEEPER.OUTCOME.SUCCESS,
            ]:
                # if the goalkeeper uses his foot or head, it's a clearance
                if head_or_foot_used:
                    clearance = event_factory.build_clearance(
                        result=None,
                        qualifiers=body_part_qualifiers,
                        **generic_event_kwargs,
                    )
                    return [clearance]
                # otherwise, it's a save
                else:
                    qualifiers.append(
                        GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)
                    )

        if qualifiers:
            goalkeeper_event = event_factory.build_goalkeeper_event(
                result=None,
                qualifiers=qualifiers + body_part_qualifiers,
                **generic_event_kwargs,
            )
            return [goalkeeper_event]

        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["type"]["name"],
            **generic_event_kwargs,
        )
        return [generic_event]

    def _create_ball_out_event(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        goalkeeper_dict = self.raw_event["goalkeeper"]
        if (
            self.raw_event.get("out", False)
            or "outcome" in goalkeeper_dict
            and "Out" in goalkeeper_dict["outcome"]["name"]
        ):
            generic_event_kwargs[
                "event_id"
            ] = f"out-{generic_event_kwargs['event_id']}"
            generic_event_kwargs["ball_state"] = BallState.DEAD
            ball_out_event = event_factory.build_ball_out(
                result=None,
                qualifiers=None,
                **generic_event_kwargs,
            )
            return [ball_out_event]
        return []


class SUBSTITUTION(EVENT):
    """StatsBomb 19/Substitution event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        team = generic_event_kwargs["team"]
        substitution_dict = self.raw_event["substitution"]

        replacement_player_id = substitution_dict["replacement"]["id"]
        replacement_player = next(
            (
                player
                for player in team.players
                if player.player_id == str(replacement_player_id)
            ),
            None,
        )

        if replacement_player is None:
            raise DeserializationError(
                f"Could not find replacement player {replacement_player_id}"
            )

        substitution_event = event_factory.build_substitution(
            result=None,
            qualifiers=None,
            replacement_player=replacement_player,
            **generic_event_kwargs,
        )
        return [substitution_event]


class BAD_BEHAVIOUR(EVENT):
    """StatsBomb 24/Bad behaviour event."""

    class CARD(Enum, metaclass=TypesEnumMeta):
        FIRST_YELLOW = 7
        SECOND_YELLOW = 6
        RED = 5

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        bad_behaviour_dict = self.raw_event.get("bad_behaviour", {})
        card_type = _get_card_type(
            EVENT_TYPE.BAD_BEHAVIOUR, bad_behaviour_dict
        )
        if card_type:
            card_event = event_factory.build_card(
                result=None,
                qualifiers=None,
                card_type=card_type,
                **generic_event_kwargs,
            )
            return [card_event]

        generic_event = event_factory.build_generic(
            result=None,
            qualifiers=None,
            event_name=self.raw_event["type"]["name"],
            **generic_event_kwargs,
        )
        return [generic_event]


class FOUL_COMMITTED(EVENT):
    """StatsBomb 22/Foul committed event."""

    class CARD(Enum, metaclass=TypesEnumMeta):
        FIRST_YELLOW = 7
        SECOND_YELLOW = 6
        RED = 5

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        foul_committed_dict = self.raw_event.get("foul_committed", {})
        card_type = _get_card_type(
            EVENT_TYPE.FOUL_COMMITTED, foul_committed_dict
        )
        if card_type:
            foul_committed_event = event_factory.build_foul_committed(
                result=None,
                qualifiers=[CardQualifier(value=card_type)],
                **generic_event_kwargs,
            )
            card_event = event_factory.build_card(
                result=None,
                qualifiers=None,
                card_type=card_type,
                **generic_event_kwargs,
            )
            return [foul_committed_event, card_event]

        foul_committed_event = event_factory.build_foul_committed(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [foul_committed_event]


class PLAYER_ON(EVENT):
    """StatsBomb 26/Player on event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        player_on_event = event_factory.build_player_on(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [player_on_event]


class PLAYER_OFF(EVENT):
    """StatsBomb 27/Player off event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        player_off_event = event_factory.build_player_off(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [player_off_event]


class BALL_RECOVERY(EVENT):
    """StatsBomb 2/Ball recovery event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        recovery_event = event_factory.build_recovery(
            result=None,
            qualifiers=None,
            **generic_event_kwargs,
        )
        return [recovery_event]


class TACTICAL_SHIFT(EVENT):
    """StatsBomb 36/Tactical shift event."""

    def _create_events(
        self, event_factory: EventFactory, **generic_event_kwargs
    ) -> List[Event]:
        formation = FORMATIONS[self.raw_event["tactics"]["formation"]]

        formation_change_event = event_factory.build_formation_change(
            result=None,
            qualifiers=None,
            formation_type=formation,
            **generic_event_kwargs,
        )
        return [formation_change_event]


def _get_card_type(
    event_type: EVENT_TYPE, event_dict: Dict
) -> Optional[CardType]:
    sb_to_kloppy_card_mappings = {
        FOUL_COMMITTED.CARD.FIRST_YELLOW: CardType.FIRST_YELLOW,
        FOUL_COMMITTED.CARD.SECOND_YELLOW: CardType.SECOND_YELLOW,
        FOUL_COMMITTED.CARD.RED: CardType.RED,
        BAD_BEHAVIOUR.CARD.FIRST_YELLOW: CardType.FIRST_YELLOW,
        BAD_BEHAVIOUR.CARD.SECOND_YELLOW: CardType.SECOND_YELLOW,
        BAD_BEHAVIOUR.CARD.RED: CardType.RED,
    }
    if "card" in event_dict:
        if event_type == EVENT_TYPE.FOUL_COMMITTED:
            card_id = FOUL_COMMITTED.CARD(event_dict["card"])
        elif event_type == EVENT_TYPE.BAD_BEHAVIOUR:
            card_id = BAD_BEHAVIOUR.CARD(event_dict["card"])
        return sb_to_kloppy_card_mappings[card_id]
    return None


def _get_body_part_qualifiers(
    event_dict: Dict,
) -> List[BodyPartQualifier]:
    sb_to_kloppy_body_part_mapping = {
        BODYPART.BOTH_HANDS: BodyPart.BOTH_HANDS,
        BODYPART.CHEST: BodyPart.CHEST,
        BODYPART.HEAD: BodyPart.HEAD,
        BODYPART.LEFT_FOOT: BodyPart.LEFT_FOOT,
        BODYPART.LEFT_HAND: BodyPart.LEFT_HAND,
        BODYPART.RIGHT_FOOT: BodyPart.RIGHT_FOOT,
        BODYPART.RIGHT_HAND: BodyPart.RIGHT_HAND,
        BODYPART.DROP_KICK: BodyPart.DROP_KICK,
        BODYPART.KEEPER_ARM: BodyPart.KEEPER_ARM,
        BODYPART.OTHER: BodyPart.OTHER,
        BODYPART.NO_TOUCH: BodyPart.NO_TOUCH,
    }

    if "body_part" in event_dict:
        body_part_id = BODYPART(event_dict["body_part"])
        if body_part_id in sb_to_kloppy_body_part_mapping:
            body_part = sb_to_kloppy_body_part_mapping[body_part_id]
            return [BodyPartQualifier(value=body_part)]

    return []


def _get_pass_qualifiers(pass_dict: Dict) -> List[PassQualifier]:
    qualifiers = []

    add_qualifier = lambda value: qualifiers.append(PassQualifier(value=value))

    if "cross" in pass_dict:
        add_qualifier(PassType.CROSS)
    if "technique" in pass_dict:
        technique_id = PASS.TECHNIQUE(pass_dict["technique"])
        if technique_id == PASS.TECHNIQUE.THROUGH_BALL:
            add_qualifier(PassType.THROUGH_BALL)
    if "switch" in pass_dict:
        add_qualifier(PassType.SWITCH_OF_PLAY)
    if "height" in pass_dict:
        height_id = PASS.HEIGHT(pass_dict["height"])
        if height_id == PASS.HEIGHT.HIGH:
            add_qualifier(PassType.HIGH_PASS)
    if "length" in pass_dict:
        pass_length = pass_dict["length"]
        if pass_length > 35:  # adopt Opta definition: 32 meters -> 35 yards
            add_qualifier(PassType.LONG_BALL)
    if "body_part" in pass_dict:
        body_part_id = BODYPART(pass_dict["body_part"])
        if body_part_id == BODYPART.HEAD:
            add_qualifier(PassType.HEAD_PASS)
        elif body_part_id == BODYPART.KEEPER_ARM:
            add_qualifier(PassType.HAND_PASS)
    if "goal_assist" in pass_dict:
        add_qualifier(PassType.ASSIST)
    return qualifiers


def _get_set_piece_qualifiers(
    event_type: EVENT_TYPE, event_dict: Dict
) -> List[SetPieceQualifier]:
    sb_to_kloppy_set_piece_mapping = {
        PASS.TYPE.CORNER_KICK: SetPieceType.CORNER_KICK,
        SHOT.TYPE.CORNER_KICK: SetPieceType.CORNER_KICK,
        PASS.TYPE.FREE_KICK: SetPieceType.FREE_KICK,
        SHOT.TYPE.FREE_KICK: SetPieceType.FREE_KICK,
        SHOT.TYPE.PENALTY: SetPieceType.PENALTY,
        PASS.TYPE.THROW_IN: SetPieceType.THROW_IN,
        PASS.TYPE.KICK_OFF: SetPieceType.KICK_OFF,
        SHOT.TYPE.KICK_OFF: SetPieceType.KICK_OFF,
        PASS.TYPE.GOAL_KICK: SetPieceType.GOAL_KICK,
    }

    if "type" in event_dict:
        type_id = None
        if event_type == EVENT_TYPE.PASS:
            type_id = PASS.TYPE(event_dict["type"]["id"])
        elif event_type == EVENT_TYPE.SHOT:
            type_id = SHOT.TYPE(event_dict["type"]["id"])
        if type_id in sb_to_kloppy_set_piece_mapping:
            set_piece_type = sb_to_kloppy_set_piece_mapping[type_id]
            return [SetPieceQualifier(value=set_piece_type)]

    return []


def event_decoder(raw_event: Dict) -> Union[EVENT, Dict]:
    type_to_event = {
        EVENT_TYPE.PASS: PASS,
        EVENT_TYPE.SHOT: SHOT,
        EVENT_TYPE.INTERCEPTION: INTERCEPTION,
        EVENT_TYPE.OWN_GOAL_FOR: OWN_GOAL_FOR,
        EVENT_TYPE.OWN_GOAL_AGAINST: OWN_GOAL_AGAINST,
        EVENT_TYPE.CLEARANCE: CLEARANCE,
        EVENT_TYPE.MISCONTROL: MISCONTROL,
        EVENT_TYPE.DRIBBLE: DRIBBLE,
        EVENT_TYPE.CARRY: CARRY,
        EVENT_TYPE.DUEL: DUEL,
        EVENT_TYPE.FIFTY_FIFTY: FIFTY_FIFTY,
        EVENT_TYPE.GOALKEEPER: GOALKEEPER,
        EVENT_TYPE.SUBSTITUTION: SUBSTITUTION,
        EVENT_TYPE.BAD_BEHAVIOUR: BAD_BEHAVIOUR,
        EVENT_TYPE.FOUL_COMMITTED: FOUL_COMMITTED,
        EVENT_TYPE.PLAYER_ON: PLAYER_ON,
        EVENT_TYPE.PLAYER_OFF: PLAYER_OFF,
        EVENT_TYPE.BALL_RECOVERY: BALL_RECOVERY,
        EVENT_TYPE.TACTICAL_SHIFT: TACTICAL_SHIFT,
    }
    event_type = EVENT_TYPE(raw_event["type"])
    event_creator = type_to_event.get(event_type, EVENT)
    return event_creator(raw_event)
