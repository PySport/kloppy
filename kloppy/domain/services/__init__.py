from collections import Counter
from typing import List, Dict

import numpy as np

from kloppy.domain import AttackingDirection, Frame, Ground, Period

from .transformers import DatasetTransformer, DatasetTransformerBuilder
from .event_factory import EventFactory, create_event

# NOT YET: from .enrichers import TrackingPossessionEnricher


def avg(items: List[float]) -> float:
    if not items:
        return 0
    return sum(items) / len(items)


def attacking_direction_from_frame(frame: Frame) -> AttackingDirection:
    """This method should only be called for the first frame of a period."""
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
        return AttackingDirection.LTR
    else:
        return AttackingDirection.RTL


def attacking_directions_from_multi_frames(
    frames: List[Frame], periods: List[Period]
) -> Dict[int, AttackingDirection]:
    """
    with only partial tracking data we cannot rely on a single frame to
    infer the attacking directions as a simple average of only some players
    x-coords might not reflect the attacking direction.
    """
    attacking_directions = {}
    frame_period_ids = np.array([_frame.period.id for _frame in frames])
    frame_attacking_directions = np.array(
        [
            attacking_direction_from_frame(frame)
            if len(frame.players_data) > 0
            else AttackingDirection.NOT_SET
            for frame in frames
        ]
    )

    for period in periods:
        period_id = period.id
        if period_id in frame_period_ids:
            count = Counter(
                frame_attacking_directions[frame_period_ids == period_id]
            )
            attacking_directions[period_id] = count.most_common()[0][0]
        else:
            attacking_directions[period_id] = AttackingDirection.NOT_SET

    return attacking_directions
