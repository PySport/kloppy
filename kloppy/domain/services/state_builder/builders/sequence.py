from dataclasses import replace, dataclass

from kloppy.domain import Event, Team, EventDataset, PassEvent
from ..builder import StateBuilder


@dataclass
class Sequence:
    sequence_id: int
    team: Team


class SequenceStateBuilder(StateBuilder):
    def initial_state(self, dataset: EventDataset) -> Sequence:
        for event in dataset.events:
            if isinstance(event, PassEvent):
                return Sequence(sequence_id=0, team=event.team)
        return Sequence(sequence_id=0, team=None)

    def reduce(self, state: Sequence, event: Event) -> Sequence:
        if state.team != event.team:
            state = replace(
                state, sequence_id=state.sequence_id + 1, team=event.team
            )
        return state
