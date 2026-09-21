from collections import defaultdict
from collections.abc import Sequence
from datetime import timedelta
from typing import Any, Optional, Union

from kloppy.domain.models.common import BallState, Player, PositionType, Team
from kloppy.domain.models.event import (
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
)
from kloppy.domain.models.formation import FormationType
from kloppy.domain.models.pitch import Point
from kloppy.domain.models.time import Period
from kloppy.domain.services.event_factory import EventFactory

from .mappings import formation_ids_mapping


def create_footovision_events(
    raw_events: list[dict], meta_data
) -> list["FootovisionEvent"]:
    footovision_events: list[FootovisionEvent] = []
    yellow_cards_by_player: dict[str, int] = {}

    for i in range(len(raw_events)):
        raw_event = raw_events[i]
        prev_raw_event = get_previous_defined_raw_event(raw_events, i)
        next_raw_event = get_next_defined_raw_event(raw_events, i)

        footovision_events.append(
            footovision_event_decoder(
                raw_event,
                prev_raw_event,
                next_raw_event,
                yellow_cards_by_player,
            )
        )
    footovision_events.extend(parse_substitution_events(meta_data))

    link_footovision_events(raw_events, footovision_events)

    return footovision_events


# Generic event type
HEADER_EVENT_TYPE = 10
FREE_KICK_EVENT_TYPE = 9

# Pass: all definitions
PASS_EVENT_TYPE = 11
SUCCESSFUL_PASS_EVENT_TYPE = 80
CROSS_EVENT_TYPE = 7
HIGH_PASS_EVENT_TYPE = 743
LONG_PASS_EVENT_TYPE = 25
THROUGH_BALL_EVENT_TYPE = 27
SWITCH_OF_PLAY_EVENT_TYPE = 52

GOALKEEPER_THROW_EVENT_TYPE = 429

SHOT_ASSIST_EVENT_TYPE = 51
ASSIST_EVENT_TYPE = 23
SECOND_SHOT_ASSIST_EVENT_TYPE = 848

GOAL_KICK_PASS_EVENT_TYPE = 86
THROW_IN_PASS_EVENT_TYPE = 17
CORNER_KICK_PASS_EVENT_TYPE = 6
KICK_OFF_PASS_EVENT_TYPE = 449

# Shot: all definitions
SHOT_EVENT_TYPE = 14
GOAL_EXCL_OWN_GOAL_EVENT_TYPE = 83
GOAL_INCL_OWN_GOAL_EVENT_TYPE = 18
SHOT_BLOCKED_EVENT_TYPE = 32
SHOT_BLOCKED_BY_DEFENSE_EVENT_TYPE = 745

# Take on: all definitions
TAKE_ON_EVENT_TYPE = 34
SUCCESSFUL_TAKE_ON_EVENT_TYPE = 450

# Carry: all definitions
CARRY_EVENT_TYPE = 841

# Clearance: all definitions
CLEARANCE_EVENT_TYPE = 35

# Duel: all definitions
DUEL_EVENT_TYPE = 3
AERIAL_DUEL_EVENT_TYPE = 31

# Card: all definitions
RED_CARD_EVENT_TYPE = 78
YELLOW_CARD_INCL_DOUBLE_EVENT_TYPE = 79

# Goalkeeper: all definitions
GOALKEEPER_SAVE_EVENT_TYPE = 307
GOALKEEPER_AIR_BLOCK_EVENT_TYPE = 301

# Others: all definitions
RECOVERY_EVENT_TYPE = 455
BALL_OUT_EVENT_TYPE = 82
FOUL_COMMITTED_EVENT_TYPE = 8
PRESSURE_EVENT_TYPE = 4
OFFSIDE_EVENT_TYPE = 408
OWN_GOAL_EVENT_TYPE = 44
GOAL_EVENT_TYPE = 18
SUBSTITUTION_EVENT_TYPE = 734

ON_BALL_EVENT_TYPE_IDS = {
    PASS_EVENT_TYPE,
    SHOT_EVENT_TYPE,
    TAKE_ON_EVENT_TYPE,
    CARRY_EVENT_TYPE,
    CLEARANCE_EVENT_TYPE,
    RECOVERY_EVENT_TYPE,
}

BALL_CONTEXT_EVENT_TYPE_IDS = ON_BALL_EVENT_TYPE_IDS | {
    BALL_OUT_EVENT_TYPE,
    FOUL_COMMITTED_EVENT_TYPE,
    OFFSIDE_EVENT_TYPE,
}


def is_footovision_ball_context_event(raw_event: dict) -> bool:
    """Whether an event is relevant when finding neighbouring ball actions.

    Offside is included as contextual information: it is needed to determine a
    preceding pass result, although it currently deserializes as a generic
    Kloppy event.
    """
    event_type_ids = set(raw_event.get("eventTypeIds", []))

    return bool(event_type_ids & BALL_CONTEXT_EVENT_TYPE_IDS)


def get_previous_defined_raw_event(
    raw_events: Sequence[dict], event_index: int
) -> Optional[dict]:
    """Return the closest supported event in the current period."""
    halftime = raw_events[event_index].get("halftime")

    for candidate in reversed(raw_events[:event_index]):
        if candidate.get("halftime") != halftime:
            break
        if is_footovision_ball_context_event(candidate):
            return candidate

    return None


def get_next_defined_raw_event(
    raw_events: Sequence[dict], event_index: int
) -> Optional[dict]:
    """Return the closest supported event in the current period."""
    halftime = raw_events[event_index].get("halftime")

    for candidate in raw_events[event_index + 1 :]:
        if candidate.get("halftime") != halftime:
            break
        if is_footovision_ball_context_event(candidate):
            return candidate

    return None


def footovision_event_decoder(
    raw_event: dict,
    prev_raw_event: Union[dict, None],
    next_raw_event: Union[dict, None],
    yellow_cards_by_player: dict[str, int],
) -> "FootovisionEvent":
    event_type_ids = raw_event.get("eventTypeIds", [])

    if PASS_EVENT_TYPE in event_type_ids:
        return FootovisionPassEvent(raw_event, prev_raw_event, next_raw_event)
    elif SHOT_EVENT_TYPE in event_type_ids:
        return FootovisionShotEvent(raw_event, prev_raw_event, next_raw_event)
    elif TAKE_ON_EVENT_TYPE in event_type_ids:
        return FootovisionTakeOnEvent(raw_event, prev_raw_event, next_raw_event)
    elif CARRY_EVENT_TYPE in event_type_ids:
        return FootovisionCarryEvent(raw_event, prev_raw_event, next_raw_event)
    elif CLEARANCE_EVENT_TYPE in event_type_ids:
        return FootovisionClearanceEvent(
            raw_event, prev_raw_event, next_raw_event
        )
    elif DUEL_EVENT_TYPE in event_type_ids:
        return FootovisionDuelEvent(raw_event, prev_raw_event, next_raw_event)
    elif (
        RED_CARD_EVENT_TYPE in event_type_ids
        or YELLOW_CARD_INCL_DOUBLE_EVENT_TYPE in event_type_ids
    ):
        return FootovisionCardEvent(
            raw_event,
            prev_raw_event,
            next_raw_event,
            yellow_cards_by_player,
        )
    elif RECOVERY_EVENT_TYPE in event_type_ids:
        return FootovisionRecoveryEvent(
            raw_event, prev_raw_event, next_raw_event
        )
    elif BALL_OUT_EVENT_TYPE in event_type_ids:
        return FootovisionBallOutEvent(
            raw_event, prev_raw_event, next_raw_event
        )
    elif FOUL_COMMITTED_EVENT_TYPE in event_type_ids:
        return FootovisionFoulCommittedEvent(
            raw_event, prev_raw_event, next_raw_event
        )
    elif PRESSURE_EVENT_TYPE in event_type_ids:
        return FootovisionPressureEvent(
            raw_event, prev_raw_event, next_raw_event
        )
    elif SUBSTITUTION_EVENT_TYPE in event_type_ids:
        return FootovisionSubstitutionEvent(
            raw_event, prev_raw_event, next_raw_event
        )

    return FootovisionGenericEvent(raw_event)


def link_footovision_events(
    raw_events: Sequence[dict],
    footovision_events: Sequence["FootovisionEvent"],
) -> None:
    """Add explicit Kloppy relations that can be safely inferred from FV data."""
    events_by_id = {
        str(event.raw_event["id"]): event for event in footovision_events
    }

    for event_index, event in enumerate(footovision_events):
        if isinstance(event, FootovisionPassEvent):
            next_raw_event = event.next_raw_event
            if next_raw_event and (
                BALL_OUT_EVENT_TYPE in next_raw_event.get("eventTypeIds", [])
                or OFFSIDE_EVENT_TYPE in next_raw_event.get("eventTypeIds", [])
            ):
                link_footovision_event_pair(
                    event,
                    events_by_id[str(next_raw_event["id"])],
                )

        if isinstance(event, FootovisionFoulCommittedEvent):
            card_raw_event = get_related_card_raw_event(raw_events, event_index)
            if card_raw_event is not None:
                link_footovision_event_pair(
                    event,
                    events_by_id[str(card_raw_event["id"])],
                )

    duels_by_time: dict[tuple[Any, Any], list[FootovisionEvent]] = defaultdict(
        list
    )
    for event in footovision_events:
        if DUEL_EVENT_TYPE in event.raw_event.get("eventTypeIds", []):
            duel_key = (
                event.raw_event.get("halftime"),
                event.raw_event.get("startTime"),
            )
            duels_by_time[duel_key].append(event)

    for duels in duels_by_time.values():
        if len(duels) == 2:
            link_footovision_event_pair(duels[0], duels[1])


def get_related_card_raw_event(
    raw_events: Sequence[dict], foul_index: int
) -> Optional[dict]:
    """Find the card caused by a foul before play resumes."""
    foul = raw_events[foul_index]
    halftime = foul.get("halftime")

    for candidate in raw_events[foul_index + 1 :]:
        if candidate.get("halftime") != halftime:
            return None

        event_type_ids = candidate.get("eventTypeIds", [])
        if (
            RED_CARD_EVENT_TYPE in event_type_ids
            or YELLOW_CARD_INCL_DOUBLE_EVENT_TYPE in event_type_ids
        ):
            if candidate.get("teamId") == foul.get("teamId") and candidate.get(
                "playerId"
            ) == foul.get("playerId"):
                return candidate
            return None

        if (
            FOUL_COMMITTED_EVENT_TYPE in event_type_ids
            or is_footovision_ball_context_event(candidate)
        ):
            return None

    return None


def link_footovision_event_pair(
    first: "FootovisionEvent", second: "FootovisionEvent"
) -> None:
    first.add_related_event_id(str(second.raw_event["id"]))
    second.add_related_event_id(str(first.raw_event["id"]))


class FootovisionEvent:
    def __init__(
        self,
        raw_event: dict[str, Any],
        prev_raw_event: Union[dict, None] = None,
        next_raw_event: Union[dict, None] = None,
        yellow_cards_dict: Optional[dict[str, int]] = None,
    ):
        self.raw_event = raw_event
        self.prev_raw_event = prev_raw_event
        self.next_raw_event = next_raw_event
        self.yellow_cards_dict = (
            yellow_cards_dict if yellow_cards_dict is not None else {}
        )
        self.period: Optional[Period] = None
        self.team: Optional[Team] = None
        self.player: Optional[Player] = None
        self.teams: Sequence[Team] = ()
        self.related_event_ids: list[str] = []

    def deserialize(self, event_factory: EventFactory) -> Sequence[Event]:
        """Deserialize the Footovision wrapper into Kloppy events."""
        raise NotImplementedError

    def set_refs(
        self,
        periods: Sequence[Period],
        teams: Sequence[Team],
    ) -> "FootovisionEvent":
        self.teams = teams
        self.period = next(
            period
            for period in periods
            if period.id == self.raw_event["halftime"]
        )
        self.team = next(
            team
            for team in teams
            if team.team_id == str(self.raw_event["teamId"])
        )
        self.player = self.team.get_player_by_id(
            str(self.raw_event["playerId"])
        )

        return self

    def get_generic_event_kwargs(self) -> dict[str, Any]:
        if self.period is None or self.team is None:
            raise RuntimeError("Call set_refs() before deserializing an event.")

        return {
            "event_id": str(self.raw_event["id"]),
            "period": self.period,
            "timestamp": timedelta(milliseconds=self.raw_event["startTime"]),
            "team": self.team,
            "player": self.player,
            "coordinates": self.get_coordinates(),
            "ball_owning_team": self.get_ball_owning_team(),
            "ball_state": self.get_ball_state(),
            "state": self.get_state(),
            "related_event_ids": self.related_event_ids,
            "raw_event": self.raw_event,
        }

    def add_related_event_id(self, event_id: str) -> None:
        if (
            event_id != str(self.raw_event["id"])
            and event_id not in self.related_event_ids
        ):
            self.related_event_ids.append(event_id)

    def get_state(self) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for raw_key, state_key in (
            ("teamPhaseId", "team_phase_id"),
            ("opponentPhaseId", "opponent_phase_id"),
            ("sequenceId", "sequence_id"),
        ):
            value = self.raw_event.get(raw_key)
            if value is not None:
                state[state_key] = value

        return state

    def get_target_player_id(self) -> Optional[str]:
        target_player_id = self.raw_event.get("targetPlayerId")
        return str(target_player_id) if target_player_id is not None else None

    def get_target_player(self) -> Optional[Player]:
        target_player_id = self.get_target_player_id()
        if target_player_id is None:
            return None

        return next(
            (
                player
                for team in self.teams
                if (player := team.get_player_by_id(target_player_id))
                is not None
            ),
            None,
        )

    def get_ball_owning_team(self) -> Optional[Team]:
        return None

    def get_ball_state(self) -> Optional[BallState]:
        return None

    def get_coordinates(self) -> Point:
        return Point(
            x=self.raw_event["startX"],
            y=self.raw_event["startY"],
        )

    def get_destination_coordinates(self) -> Point:
        return Point(
            x=self.raw_event["endX"],
            y=self.raw_event["endY"],
        )

    def get_end_timestamp(self) -> timedelta:
        return timedelta(milliseconds=self.raw_event["endTime"])

    def get_body_part_qualifiers(self) -> list[BodyPartQualifier]:
        if HEADER_EVENT_TYPE in self.raw_event.get("eventTypeIds", []):
            return [BodyPartQualifier(BodyPart.HEAD)]
        return []

    def is_during_counter_attack(self) -> bool:
        return False

    def get_counter_attack_qualifiers(self) -> list[CounterAttackQualifier]:
        if self.is_during_counter_attack():
            return [CounterAttackQualifier(value=True)]
        return []


class FootovisionOnBallEvent(FootovisionEvent):
    """Base class for events where the actor is known to control the ball."""

    def get_ball_owning_team(self) -> Optional[Team]:
        return self.team

    def get_ball_state(self) -> BallState:
        return BallState.ALIVE


class FootovisionPassEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_pass(
                **self.get_generic_event_kwargs(),
                result=self.get_pass_result(),
                receiver_coordinates=self.get_destination_coordinates(),
                receiver_player=self.get_receiver_player(),
                receive_timestamp=self.get_end_timestamp(),
                qualifiers=self.get_pass_qualifiers(),
            )
        ]

    def get_pass_result(self) -> PassResult:
        if SUCCESSFUL_PASS_EVENT_TYPE in self.raw_event.get("eventTypeIds", []):
            return PassResult.COMPLETE
        elif (
            self.next_raw_event
            and BALL_OUT_EVENT_TYPE
            in self.next_raw_event.get("eventTypeIds", [])
        ):
            return PassResult.OUT
        elif (
            self.next_raw_event
            and OFFSIDE_EVENT_TYPE
            in self.next_raw_event.get("eventTypeIds", [])
        ):
            return PassResult.OFFSIDE
        else:
            return PassResult.INCOMPLETE

    def get_receiver_player(self) -> Optional[Player]:
        if self.team is None:
            return None

        target_player_id = self.raw_event.get("targetPlayerId")
        if target_player_id is None:
            return None

        return self.team.get_player_by_id(str(target_player_id))

    def get_pass_qualifiers(
        self,
    ) -> list[
        Union[
            PassQualifier,
            BodyPartQualifier,
            SetPieceQualifier,
            CounterAttackQualifier,
        ]
    ]:
        event_type_ids = set(self.raw_event.get("eventTypeIds", []))

        qualifiers: list[
            Union[
                PassQualifier,
                BodyPartQualifier,
                SetPieceQualifier,
                CounterAttackQualifier,
            ]
        ] = []

        pass_type_mapping = {
            HEADER_EVENT_TYPE: PassType.HEAD_PASS,
            CROSS_EVENT_TYPE: PassType.CROSS,
            HIGH_PASS_EVENT_TYPE: PassType.HIGH_PASS,
            LONG_PASS_EVENT_TYPE: PassType.LONG_BALL,
            THROUGH_BALL_EVENT_TYPE: PassType.THROUGH_BALL,
            SWITCH_OF_PLAY_EVENT_TYPE: PassType.SWITCH_OF_PLAY,
            GOALKEEPER_THROW_EVENT_TYPE: PassType.HAND_PASS,
        }
        assist_type_mapping = {
            SHOT_ASSIST_EVENT_TYPE: PassType.SHOT_ASSIST,
            ASSIST_EVENT_TYPE: PassType.ASSIST,
            SECOND_SHOT_ASSIST_EVENT_TYPE: PassType.ASSIST_2ND,
        }
        set_piece_mapping = {
            FREE_KICK_EVENT_TYPE: SetPieceType.FREE_KICK,
            GOAL_KICK_PASS_EVENT_TYPE: SetPieceType.GOAL_KICK,
            THROW_IN_PASS_EVENT_TYPE: SetPieceType.THROW_IN,
            CORNER_KICK_PASS_EVENT_TYPE: SetPieceType.CORNER_KICK,
            KICK_OFF_PASS_EVENT_TYPE: SetPieceType.KICK_OFF,
        }

        for event_type_id, pass_type in pass_type_mapping.items():
            if event_type_id in event_type_ids:
                qualifiers.append(PassQualifier(value=pass_type))

        if len(qualifiers) == 0:
            qualifiers.append(PassQualifier(value=PassType.SIMPLE_PASS))

        for event_type_id, pass_type in assist_type_mapping.items():
            if event_type_id in event_type_ids:
                qualifiers.append(PassQualifier(value=pass_type))

        for event_type_id, set_piece_type in set_piece_mapping.items():
            if event_type_id in event_type_ids:
                qualifiers.append(SetPieceQualifier(value=set_piece_type))

        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(True))

        qualifiers.extend(list(self.get_body_part_qualifiers()))

        return qualifiers


class FootovisionCarryEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_carry(
                **self.get_generic_event_kwargs(),
                end_timestamp=self.get_end_timestamp(),
                end_coordinates=self.get_destination_coordinates(),
                result=self.get_carry_result(),
                qualifiers=self.get_carry_qualifiers(),
            )
        ]

    def get_carry_result(self) -> CarryResult:
        if self.next_raw_event and self.next_raw_event.get(
            "teamId"
        ) != self.raw_event.get("teamId"):
            return CarryResult.INCOMPLETE

        return CarryResult.COMPLETE

    def get_carry_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []

        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionShotEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_shot(
                **self.get_generic_event_kwargs(),
                result=self.get_shot_result(),
                result_coordinates=self.get_destination_coordinates(),
                qualifiers=self.get_shot_qualifiers(),
            )
        ]

    def get_shot_result(self) -> ShotResult:
        event_type_ids = set(self.raw_event.get("eventTypeIds", []))

        if OWN_GOAL_EVENT_TYPE in event_type_ids:
            return ShotResult.OWN_GOAL

        if GOAL_EXCL_OWN_GOAL_EVENT_TYPE in event_type_ids:
            return ShotResult.GOAL

        if SHOT_BLOCKED_EVENT_TYPE in event_type_ids:
            if SHOT_BLOCKED_BY_DEFENSE_EVENT_TYPE in event_type_ids:
                return ShotResult.BLOCKED
            return ShotResult.SAVED

        return ShotResult.OFF_TARGET

    def get_shot_qualifiers(
        self,
    ) -> list[
        Union[BodyPartQualifier, SetPieceQualifier, CounterAttackQualifier]
    ]:
        qualifiers: list[
            Union[BodyPartQualifier, SetPieceQualifier, CounterAttackQualifier]
        ] = list(self.get_body_part_qualifiers())

        if FREE_KICK_EVENT_TYPE in self.raw_event.get("eventTypeIds", []):
            qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))

        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionDuelEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_duel(
                **self.get_generic_event_kwargs(),
                result=self.get_duel_result(),
                qualifiers=self.get_duel_qualifiers(),
            )
        ]

    def get_duel_result(self) -> Optional[DuelResult]:
        if self.next_raw_event and self.next_raw_event.get(
            "playerId"
        ) == self.raw_event.get("playerId"):
            return DuelResult.WON
        else:
            return DuelResult.LOST

    def get_state(self) -> dict[str, Any]:
        state = super().get_state()
        opponent_player_id = self.get_target_player_id()
        if opponent_player_id is not None:
            state["opponent_player_id"] = opponent_player_id

        opponent_player = self.get_target_player()
        if opponent_player is not None:
            state["opponent_player"] = opponent_player

        return state

    def get_duel_qualifiers(
        self,
    ) -> list[Union[DuelQualifier, CounterAttackQualifier]]:
        qualifiers = []

        if AERIAL_DUEL_EVENT_TYPE in self.raw_event.get("eventTypeIds", []):
            qualifiers.append(DuelQualifier(value=DuelType.AERIAL))
        else:
            qualifiers.append(DuelQualifier(value=DuelType.GROUND))

        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionGenericEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_generic(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=None,
            )
        ]


class FootovisionTakeOnEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_take_on(
                **self.get_generic_event_kwargs(),
                result=self.get_take_on_result(),
                qualifiers=self.get_take_on_qualifiers(),
            )
        ]

    def get_take_on_result(self) -> Optional[TakeOnResult]:
        if SUCCESSFUL_TAKE_ON_EVENT_TYPE in self.raw_event.get(
            "eventTypeIds", []
        ):
            return TakeOnResult.COMPLETE
        else:
            if (
                self.next_raw_event
                and BALL_OUT_EVENT_TYPE
                in self.next_raw_event.get("eventTypeIds", [])
            ):
                return TakeOnResult.OUT

            return TakeOnResult.INCOMPLETE

    def get_take_on_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionClearanceEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_clearance(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=self.get_clearance_qualifiers(),
            )
        ]

    def get_clearance_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionInterceptionEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_interception(
                **self.get_generic_event_kwargs(),
                result=self.get_interception_result(),
                qualifiers=self.get_interception_qualifiers(),
            )
        ]

    def get_interception_result(self) -> Optional[InterceptionResult]:
        if self.next_raw_event and self.next_raw_event.get(
            "playerId"
        ) == self.raw_event.get("playerId"):
            if BALL_OUT_EVENT_TYPE in self.next_raw_event.get(
                "eventTypeIds", []
            ):
                return InterceptionResult.OUT
            else:
                return InterceptionResult.SUCCESS
        else:
            return InterceptionResult.LOST

    def get_interception_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionCardEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        card_type = self.get_card_type()
        if card_type is None:
            return []
        return [
            event_factory.build_card(
                **self.get_generic_event_kwargs(),
                card_type=card_type,
                result=None,
                qualifiers=None,
            )
        ]

    def get_card_type(self) -> CardType:
        event_type_ids = self.raw_event.get("eventTypeIds", [])

        if RED_CARD_EVENT_TYPE in event_type_ids:
            return CardType.RED

        player_id = str(self.raw_event["playerId"])
        previous_yellows = self.yellow_cards_dict.get(player_id, 0)

        self.yellow_cards_dict[player_id] = previous_yellows + 1

        if previous_yellows >= 1:
            return CardType.SECOND_YELLOW

        return CardType.FIRST_YELLOW


class FootovisionRecoveryEvent(FootovisionOnBallEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_recovery(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=self.get_recovery_qualifiers(),
            )
        ]

    def get_recovery_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionMiscontrolEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_miscontrol(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=self.get_miscontrol_qualifiers(),
            )
        ]

    def get_miscontrol_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionBallOutEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_ball_out(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=self.get_ball_out_qualifiers(),
            )
        ]

    def get_ball_out_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionFoulCommittedEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_foul_committed(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=self.get_foul_qualifiers(),
            )
        ]

    def get_foul_qualifiers(
        self,
    ) -> list[Union[CounterAttackQualifier, CardQualifier]]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers


class FootovisionGoalkeeperEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_goalkeeper_event(
                **self.get_generic_event_kwargs(),
                result=None,
                qualifiers=self.get_goalkeeper_qualifiers(),
            )
        ]

    def get_goalkeeper_qualifiers(
        self,
    ) -> list[Union[CounterAttackQualifier, GoalkeeperQualifier]]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        if GOALKEEPER_SAVE_EVENT_TYPE in self.raw_event.get("eventTypeIds", []):
            qualifiers.append(
                GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)
            )

        if GOALKEEPER_AIR_BLOCK_EVENT_TYPE in self.raw_event.get(
            "eventTypeIds", []
        ):
            if self.next_raw_event and self.next_raw_event.get(
                "playerId"
            ) == self.raw_event.get("playerId"):
                qualifiers.append(
                    GoalkeeperQualifier(value=GoalkeeperActionType.CLAIM)
                )
            else:
                qualifiers.append(
                    GoalkeeperQualifier(value=GoalkeeperActionType.PUNCH)
                )

        return qualifiers


class FootovisionPressureEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_pressure_event(
                **self.get_generic_event_kwargs(),
                end_timestamp=self.get_pressure_end_timestamp(),
                result=None,
                qualifiers=self.get_pressure_qualifiers(),
            )
        ]

    def get_pressure_end_timestamp(self) -> timedelta:
        # TODO: override if Footovision pressure timing differs from endTime.
        return self.get_end_timestamp()

    def get_state(self) -> dict[str, Any]:
        state = super().get_state()
        pressured_player_id = self.get_target_player_id()
        if pressured_player_id is not None:
            state["pressured_player_id"] = pressured_player_id

        pressured_player = self.get_target_player()
        if pressured_player is not None:
            state["pressured_player"] = pressured_player

        return state

    def get_pressure_qualifiers(self) -> list[CounterAttackQualifier]:
        qualifiers = []
        if self.is_during_counter_attack():
            qualifiers.append(CounterAttackQualifier(value=True))

        return qualifiers

class FootovisionSubstitutionEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        replacement_player = self.get_replacement_player()

        if replacement_player is None:
            raise RuntimeError(
                f"Could not find replacement player for substitution event {self.raw_event}"
            )

        return [
            event_factory.build_substitution(
                **self.get_generic_event_kwargs(),
                replacement_player=replacement_player,
            )
        ]

    def get_replacement_player(self) -> Optional[Player]:
        if self.team is None:
            return None

        replacement_player_id = self.raw_event.get("playerId")
        if replacement_player_id is None:
            return None

        return self.team.get_player_by_id(str(replacement_player_id))


class FootovisionPlayerOnEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_player_on(
                **self.get_generic_event_kwargs(), result=None, qualifiers=None
            )
        ]


class FootovisionPlayerOffEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        return [
            event_factory.build_player_off(
                **self.get_generic_event_kwargs(), result=None, qualifiers=None
            )
        ]


class FootovisionFormationChangeEvent(FootovisionEvent):
    def deserialize(self, event_factory: EventFactory):
        formation_type = self.get_formation_type()
        if formation_type is None:
            return []
        return [
            event_factory.build_formation_change(
                **self.get_generic_event_kwargs(),
                formation_type=formation_type,
                player_positions=self.get_player_positions(),
                result=None,
                qualifiers=None,
            )
        ]

    def get_formation_type(self) -> Optional[FormationType]:
        return formation_ids_mapping.get(
            self.formation.get("system"),
            FormationType.UNKNOWN,
        )

    def get_player_positions(self) -> Optional[dict[Player, PositionType]]:

        return None

class FootovisionSubClass:
    def __init__(
        self,
        formation: dict[str, Any],
        reason: dict[str, Any],
        team_id: Any,
    ):
        self.formation = formation
        self.reason = reason
        self.team_id = team_id

        self.period: Optional[Period] = None
        self.team: Optional[Team] = None
        self.player: Optional[Player] = None
        self.teams: Sequence[Team] = ()
        self.related_event_ids: list[str] = []

    def deserialize(self, event_factory: EventFactory) -> Sequence[Event]:
        """Deserialize the Footovision wrapper into Kloppy events."""
        raise NotImplementedError

    def set_refs(
        self,
        periods: Sequence[Period],
        teams: Sequence[Team],
    ):
        period_id = int(self.formation["halftime"])
        team_id = str(self.team_id)

        self.period = next(
            (period for period in periods if period.id == period_id),
            None,
        )
        if self.period is None:
            raise ValueError(f"Could not find period with id={period_id}")

        self.team = next(
            (team for team in teams if team.team_id == team_id),
            None,
        )
        if self.team is None:
            raise ValueError(f"Could not find team with id={team_id}")

        # The main player in a substitution event is the player going out.
        self.player = self.team.get_player_by_id(str(self.reason["playerOut"]))
        if self.player is None:
            raise ValueError(
                f"Could not find outgoing player "
                f"{self.reason['playerOut']!r} in team {team_id}"
            )

        return self

    def get_generic_event_kwargs(self) -> dict[str, Any]:
        if self.period is None or self.team is None or self.player is None:
            raise RuntimeError("Call set_refs() before deserializing an event.")

        return {
            "period": self.period,
            "timestamp": timedelta(milliseconds=self.formation["time"]),
            "team": self.team,
            "player": self.player,
            "ball_state": BallState.DEAD,
        }

    def get_replacement_player(self) -> Optional[Player]:
        if self.team is None:
            return None

        return self.team.get_player_by_id(str(self.reason["playerIn"]))




def parse_substitution_events(
    meta_data: dict[str, Any],
) -> list[FootovisionSubstitutionEvent]:
    teams_data = (
        (
            meta_data["homeTeamFormations"],
            meta_data["homeTeamId"],
        ),
        (
            meta_data["awayTeamFormations"],
            meta_data["awayTeamId"],
        ),
    )

    substitution_events = []

    for formations, team_id in teams_data:
        substitution_events.extend(
            parse_team_substitution_events(
                formations=formations,
                team_id=team_id,
            )
        )

    return substitution_events


def parse_team_substitution_events(
    formations: Sequence[dict[str, Any]],
    team_id: Any,
) -> list[FootovisionSubstitutionEvent]:
    substitution_events = []

    for formation in formations:
        reasons = formation.get("reasonForFormationChange") or []

        for reason in reasons:
            if reason.get("type") != "substitution":
                continue

            substitution_events.append(
                FootovisionSubstitutionEvent(
                    formation=formation,
                    reason=reason,
                    team_id=team_id,
                )
            )

    return substitution_events
