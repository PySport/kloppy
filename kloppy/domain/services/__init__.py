from typing import List

from kloppy.domain import AttackingDirection, Frame, Ground

from .transformers import DatasetTransformer
from .event_factory import EventFactory, create_event

# NOT YET: from .enrichers import TrackingPossessionEnricher


def avg(items: List[float]) -> float:
    if not items:
        return 0
    return sum(items) / len(items)


def attacking_direction_from_frame(frame: Frame) -> AttackingDirection:
    """This method should only be called for the first frame of a"""
    avg_x_home = avg(
        [
            player_data.coordinates.x
            for player, player_data in frame.players_data.items()
            if player.team.ground == Ground.HOME
        ]
    )
    avg_x_away = avg(
        [
            player_data.coordinates.x
            for player, player_data in frame.players_data.items()
            if player.team.ground == Ground.AWAY
        ]
    )

    if avg_x_home < avg_x_away:
        return AttackingDirection.HOME_AWAY
    else:
        return AttackingDirection.AWAY_HOME
