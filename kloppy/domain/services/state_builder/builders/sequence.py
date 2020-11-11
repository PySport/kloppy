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
)
from ..builder import StateBuilder

OPEN_SEQUENCE = (PassEvent, CarryEvent, RecoveryEvent)
CLOSE_SEQUENCE = (BallOutEvent, FoulCommittedEvent, ShotEvent)


@dataclass
class Sequence:
    sequence_id: int
    team: Team


class SequenceStateBuilder(StateBuilder):
    def __init__(self):
        self.sequence_open = False

    def initial_state(self, dataset: EventDataset) -> Sequence:
        for event in dataset.events:
            if isinstance(event, OPEN_SEQUENCE):
                self.sequence_open = True
                return Sequence(sequence_id=0, team=event.team)
        return Sequence(sequence_id=0, team=None)

    def reduce(self, state: Sequence, event: Event) -> Sequence:

        if self.sequence_open and isinstance(event, CLOSE_SEQUENCE):
            state = replace(
                state, sequence_id=state.sequence_id + 1, team=None
            )

        if not self.sequence_open and isinstance(event, OPEN_SEQUENCE):
            state = replace(
                state, sequence_id=state.sequence_id + 1, team=event.team
            )

        return state
