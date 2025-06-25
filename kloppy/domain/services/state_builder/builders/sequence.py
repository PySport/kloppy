from dataclasses import replace, dataclass
from typing import Optional

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
)
from ..builder import StateBuilder


@dataclass
class Sequence:
    sequence_id: int
    team: Team


CLOSE_SEQUENCE = (BallOutEvent, FoulCommittedEvent, ShotEvent)


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
    else:
        return False


def should_open_sequence(
    event: Event, next_event: Event, state: Optional[Sequence] = None
) -> bool:
    can_open_sequence = False
    if is_possessing_event(event):
        can_open_sequence = True
    elif (
        isinstance(event, DuelEvent)
        and event.result == DuelResult.WON
        and is_possessing_event(next_event)
    ):
        can_open_sequence = True
    return can_open_sequence and (
        state is None
        or state.team != event.team
        or event.get_qualifier_value(SetPieceQualifier)
    )


def should_close_sequence(event: Event) -> bool:
    if isinstance(event, CLOSE_SEQUENCE):
        return True
    return False


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
