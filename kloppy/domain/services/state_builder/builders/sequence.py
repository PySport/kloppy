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
)
from ..builder import StateBuilder


@dataclass
class Sequence:
    sequence_id: int
    team: Team


CLOSE_SEQUENCE = (BallOutEvent, FoulCommittedEvent, ShotEvent)


def should_open_sequence(
    event: Event, state: Optional[Sequence] = None
) -> bool:
    open_sequence = False
    if isinstance(event, (PassEvent, CarryEvent, RecoveryEvent, TakeOnEvent)):
        open_sequence = True
    if isinstance(event, GoalkeeperEvent):
        open_sequence = event.get_qualifier_value(GoalkeeperQualifier) in [
            GoalkeeperActionType.PICK_UP,
            GoalkeeperActionType.CLAIM,
        ]
    if isinstance(event, InterceptionEvent):
        open_sequence = event.result == InterceptionResult.SUCCESS
    return open_sequence and (
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
            if should_open_sequence(event):
                return Sequence(sequence_id=0, team=event.team)
        return Sequence(sequence_id=0, team=None)

    def reduce_before(self, state: Sequence, event: Event) -> Sequence:
        if should_open_sequence(event, state):
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
