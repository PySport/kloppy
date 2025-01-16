from dataclasses import replace, dataclass

from kloppy.domain import (
    Event,
    Team,
    Time,
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
    start: Time
    end: Time


class SequenceStateBuilder(StateBuilder):
    current_sequence: Sequence

    def initial_state(self, dataset: EventDataset) -> Sequence:
        self.current_sequence = Sequence(
            sequence_id=0, team=None, start=None, end=None
        )
        return self.current_sequence

    def reduce_before(self, state: Sequence, event: Event) -> Sequence:
        if isinstance(event, OPEN_SEQUENCE) and (
            state.team != event.team
            or event.get_qualifier_value(SetPieceQualifier)
        ):
            # Finalize the current sequence
            self.current_sequence.end = event.time

            # Start a new sequence
            self.current_sequence = replace(
                state,
                sequence_id=state.sequence_id + 1,
                team=event.team,
                start=event.time,
                end=None,
            )
            state = self.current_sequence

        return state

    def reduce_after(self, state: Sequence, event: Event) -> Sequence:
        if isinstance(event, CLOSE_SEQUENCE):
            # Finalize the current sequence
            self.current_sequence.end = event.time

            # Start a new sequence
            self.current_sequence = replace(
                state,
                sequence_id=state.sequence_id + 1,
                team=None,
                start=event.time,
                end=None,
            )
            state = self.current_sequence

        return state
