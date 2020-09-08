from dataclasses import dataclass
from typing import Set

from kloppy.domain import (
    Event,
    EventDataset,
    Player,
    SubstitutionEvent,
    PlayerOffEvent,
    PlayerOnEvent,
    CardEvent,
    CardType,
    Provider,
)
from ..builder import StateBuilder


@dataclass
class Lineup:
    players: Set[Player]


class LineupStateBuilder(StateBuilder):
    def initial_state(self, dataset: EventDataset) -> Lineup:
        if dataset.metadata.provider != Provider.STATSBOMB:
            raise Exception(
                "Lineup state can only be applied to statsbomb data"
            )

        return Lineup(
            players=(
                set(
                    player
                    for player in dataset.metadata.teams[0].players
                    if player.starting
                )
                | set(
                    player
                    for player in dataset.metadata.teams[1].players
                    if player.starting
                )
            )
        )

    def reduce(self, state: Lineup, event: Event) -> Lineup:
        if isinstance(event, SubstitutionEvent):
            state = Lineup(
                players=state.players - {event.player}
                | {event.replacement_player}
            )
        elif isinstance(event, PlayerOffEvent):
            state = Lineup(players=state.players - {event.player})
        elif isinstance(event, PlayerOnEvent):
            state = Lineup(players=state.players | {event.player})
        elif isinstance(event, CardEvent):
            if event.card_type in (CardType.SECOND_YELLOW, CardType.RED):
                state = Lineup(players=state.players - {event.player})
        return state
