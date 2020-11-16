from dataclasses import replace, dataclass

from kloppy.domain import ShotEvent, Event, Ground, ShotResult, EventDataset
from ..builder import StateBuilder


@dataclass
class Score:
    home: int
    away: int

    def __str__(self):
        return f"{self.home}-{self.away}"


class ScoreStateBuilder(StateBuilder):
    def initial_state(self, dataset: EventDataset) -> Score:
        return Score(home=0, away=0)

    def reduce_before(self, state: Score, event: Event) -> Score:
        return state

    def reduce_after(self, state: Score, event: Event) -> Score:
        if isinstance(event, ShotEvent):
            if event.result == ShotResult.GOAL:
                if event.team.ground == Ground.HOME:
                    state = replace(state, home=state.home + 1)
                else:
                    state = replace(state, away=state.away + 1)
        return state
