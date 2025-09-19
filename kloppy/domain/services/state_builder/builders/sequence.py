from dataclasses import replace, dataclass
from typing import Optional, List

from kloppy.domain import (
    Event,
    Team,
    EventDataset,
    PassEvent,
    CarryEvent,
    RecoveryEvent,
    BallOutEvent,
    FoulCommittedEvent,
    ShotEvent,
    SetPieceQualifier,
    GoalkeeperEvent,
    GoalkeeperActionType,
    TakeOnEvent,
    InterceptionEvent,
    InterceptionResult,
    GoalkeeperQualifier,
    DuelEvent,
    DuelResult,
    GenericEvent,
    PlayerOnEvent,
    CardEvent,
    SubstitutionEvent,
    PlayerOffEvent,
    FormationChangeEvent,
    ClearanceEvent,
)
from kloppy.domain.models.event import (
    PossessionSwitchQualifier,
    PossessionSwitchType,
    EventType,
)
from ..builder import StateBuilder


@dataclass
class Sequence:
    sequence_id: Optional[int]
    team: Optional[Team]


EXCLUDED_OFF_BALL_EVENTS = (
    GenericEvent,
    SubstitutionEvent,
    CardEvent,
    PlayerOnEvent,
    PlayerOffEvent,
    FormationChangeEvent,
)

CLOSE_SEQUENCE = (BallOutEvent, FoulCommittedEvent, ShotEvent)


def is_ball_winning_defensive_action(event: Event) -> bool:
    if isinstance(event, DuelEvent) and event.result == DuelResult.WON:
        return True
    elif isinstance(event, ClearanceEvent):
        return True


def is_possessing_event(event: Event) -> bool:
    if isinstance(event, (PassEvent, CarryEvent, RecoveryEvent, TakeOnEvent)):
        return True
    elif isinstance(event, GoalkeeperEvent) and event.get_qualifier_value(
        GoalkeeperQualifier
    ) in [
        GoalkeeperActionType.PICK_UP,
        GoalkeeperActionType.CLAIM,
    ]:
        return True
    elif (
        isinstance(event, InterceptionEvent)
        and event.result == InterceptionResult.SUCCESS
    ):
        return True


def should_open_sequence(
    event: Event, next_event: Optional[Event], state: Optional[Sequence] = None
) -> bool:
    can_open_sequence = False
    if is_possessing_event(event):
        can_open_sequence = True
    elif (
        is_ball_winning_defensive_action(event)
        and next_event is not None
    ):
        if (
                all(isinstance(e, DuelEvent) for e in (event, next_event))
                and next_event.result == DuelResult.LOST
        ):
            next_event = next_event.next_record
        can_open_sequence = next_event.team == event.team and is_possessing_event(next_event)
    return can_open_sequence and (
        state is None
        or state.team != event.team
        or event.get_qualifier_value(SetPieceQualifier)
    )


def should_close_sequence(event: Event) -> bool:
    if isinstance(event, CLOSE_SEQUENCE):
        return True


class SequenceStateBuilder(StateBuilder):
    def initial_state(self, dataset: EventDataset) -> Sequence:
        for event in dataset.events:
            if should_open_sequence(event, event.next_record):
                return Sequence(sequence_id=0, team=event.team)
        return Sequence(sequence_id=0, team=None)

    def reduce_before(self, state: Sequence, event: Event) -> Sequence:
        if should_open_sequence(event, event.next_record, state):
            state = replace(
                state, sequence_id=state.sequence_id + 1, team=event.team
            )

        return state

    def reduce_after(self, state: Sequence, event: Event) -> Sequence:
        if isinstance(event, CLOSE_SEQUENCE):
            state = replace(
                state, sequence_id=state.sequence_id + 1, team=None
            )

        return state

    def post_process(self, events: List[Event]):
        current_sequence_id = 1
        sequence_id_mapping = {}
        first_events = {}
        last_events = {}
        sequence_teams = {}

        for event in events:
            sequence = event.state["sequence"]

            if (
                isinstance(event, EXCLUDED_OFF_BALL_EVENTS)
                or sequence.team is None
            ):
                event.state["sequence"] = Sequence(sequence_id=None, team=None)
            elif sequence.sequence_id is not None:
                # Map old sequence IDs to new consecutive IDs
                # Get or assign a new sequence ID
                new_sequence_id = sequence_id_mapping.setdefault(
                    sequence.sequence_id, current_sequence_id
                )
                if new_sequence_id == current_sequence_id:
                    current_sequence_id += 1
                # Assign the new sequence ID
                event.state["sequence"] = Sequence(
                    sequence_id=new_sequence_id, team=sequence.team
                )
                sequence_teams.setdefault(new_sequence_id, sequence.team)

                if (
                    event.event_type
                    not in [EventType.PRESSURE, EventType.BALL_OUT]
                    and event.team.team_id == sequence.team.team_id
                ):
                    # track first & last event per sequence
                    if new_sequence_id not in first_events:
                        first_events[new_sequence_id] = event
                    last_events[new_sequence_id] = event

        # mark events as possession gain/lose
        for seq_id, first_event in first_events.items():
            if sequence_teams.get(seq_id - 1, None) == sequence_teams[seq_id]:
                continue  # previous sequence is by same team, so no possession gain
            if not first_event.get_qualifier_value(SetPieceQualifier):
                first_event.qualifiers = first_event.qualifiers or []
                first_event.qualifiers.append(
                    PossessionSwitchQualifier(PossessionSwitchType.GAIN)
                )
        for seq_id, last_event in last_events.items():
            if sequence_teams.get(seq_id + 1, None) == sequence_teams[seq_id]:
                continue  # next sequence is by same team, so no possession loss
            if last_event.event_type != EventType.SHOT:
                last_event.qualifiers = last_event.qualifiers or []
                last_event.qualifiers.append(
                    PossessionSwitchQualifier(PossessionSwitchType.LOSE)
                )
