from dataclasses import replace, dataclass

from kloppy.domain import (
    FormationChangeEvent,
    Event,
    Ground,
    EventDataset,
    FormationType,
)
from ..builder import StateBuilder


@dataclass
class Formation:
    home: FormationType
    away: FormationType

    def __str__(self):
        return f"{self.home} {self.away}"


class FormationStateBuilder(StateBuilder):
    def initial_state(self, dataset: EventDataset) -> Formation:
        home_team, away_team = dataset.metadata.teams
        home_formation = home_team.starting_formation
        away_formation = away_team.starting_formation

        return Formation(home=home_formation, away=away_formation)

    def reduce_before(self, state: Formation, event: Event) -> Formation:
        return state

    def reduce_after(self, state: Formation, event: Event) -> Formation:
        if isinstance(event, FormationChangeEvent):
            if event.team.ground == Ground.HOME:
                state = replace(state, home=event.formation.value)
            else:
                state = replace(state, away=event.formation.value)
        return state
