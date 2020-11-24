from dataclasses import replace, dataclass

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
)
from ..builder import StateBuilder

OPEN_SEQUENCE = (PassEvent, CarryEvent, RecoveryEvent)
CLOSE_SEQUENCE = (BallOutEvent, FoulCommittedEvent, ShotEvent)


@dataclass
class Sequence:
    sequence_id: int
    team: Team


class SequenceStateBuilder(StateBuilder):
    def initial_state(self, dataset: EventDataset) -> Sequence:
        for event in dataset.events:
            if isinstance(event, OPEN_SEQUENCE):
                return Sequence(sequence_id=0, team=event.team)
        return Sequence(sequence_id=0, team=None)

    def reduce_before(self, state: Sequence, event: Event) -> Sequence:
        if isinstance(event, OPEN_SEQUENCE) and (
            state.team != event.team
            or event.get_qualifier_value(SetPieceQualifier)
        ):
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
