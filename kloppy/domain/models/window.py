from dataclasses import dataclass
from typing import Set, List, Any

from kloppy.domain.models.common import Score, Player, Ground, Team
from kloppy.domain.models.event import Event


@dataclass(frozen=True)
class State:
    score: Score
    players: Set[Player]

    def remove_player(self, player: Player) -> 'State':
        return State(
            players=self.players - {player},
            score=self.score
        )

    def add_player(self, player: Player) -> 'State':
        return State(
            players=self.players | {player},
            score=self.score
        )

    def add_goal(self, team: Team) -> 'State':
        if team.ground == Ground.HOME:
            score = Score(home=self.score.home + 1, away=self.score.away)
        elif team.ground == Ground.AWAY:
            score = Score(home=self.score.home, away=self.score.away + 1)
        else:
            raise Exception(f"Unknown ground {team.ground}")

        return State(
            players=self.players,
            score=score
        )

    def add_away_goal(self) -> 'State':
        return State(
            players=self.players,
            score=Score(home=self.score.home + 1, away=self.score.away)
        )


@dataclass(frozen=True)
class Window:
    state: State
    key: Any
    events: List[Event]

    @property
    def start_timestamp(self):
        return self.events[0].timestamp

    @property
    def end_timestamp(self):
        return self.events[-1].timestamp

    @property
    def duration(self):
        return self.end_timestamp - self.start_timestamp

    @property
    def period(self):
        return self.events[0].period


__all__ = [
    "State",
    "Window"
]
