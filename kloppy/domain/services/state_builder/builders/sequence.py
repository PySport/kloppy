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
    # current_sequence is mutable by design so every event in the sequence can be updated with the correct times
    current_sequence: Sequence

    def initial_state(self, dataset: EventDataset) -> Sequence:
        self.current_sequence = Sequence(
            sequence_id=0, team=None, start=None, end=None
        )
        return self.current_sequence

    def reduce_before(self, state: Sequence, event: Event) -> Sequence:
        # Set the start time of the sequence if it is not set yet
        if self.current_sequence.start is None:
            self.current_sequence.start = event.time

        if isinstance(event, OPEN_SEQUENCE) and (
            state.team != event.team
            or event.get_qualifier_value(SetPieceQualifier)
        ):
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
        # Always update the end time of the sequence
        # This ensures sequences without CLOSE_SEQUENCE events still have the correct time
        self.current_sequence.end = event.time

        if isinstance(event, CLOSE_SEQUENCE):
            # Start a new sequence
            self.current_sequence = replace(
                state,
                sequence_id=state.sequence_id + 1,
                team=None,
                start=None,
                end=None,
            )
            state = self.current_sequence

        return state
