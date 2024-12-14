from datetime import timedelta
from typing import List, NamedTuple, Union

from kloppy.domain import EventDataset, Player, Time, PositionType
from kloppy.domain.services.aggregators.aggregator import (
    EventDatasetAggregator,
)


class MinutesPlayed(NamedTuple):
    player: Player
    start_time: Time
    end_time: Time
    duration: timedelta


class MinutesPlayedPerPosition(NamedTuple):
    player: Player
    position: PositionType
    start_time: Time
    end_time: Time
    duration: timedelta


class MinutesPlayedAggregator(EventDatasetAggregator):
    def __init__(self, include_position: bool = False):
        self.include_position = include_position

    def aggregate(
        self, dataset: EventDataset
    ) -> List[Union[MinutesPlayedPerPosition, MinutesPlayed]]:
        items = []

        for team in dataset.metadata.teams:
            for player in team.players:
                if not self.include_position:
                    _start_time = None
                    end_time = None
                    for (
                        start_time,
                        end_time,
                        position,
                    ) in player.positions.ranges():
                        if not _start_time:
                            _start_time = start_time

                    if _start_time:
                        items.append(
                            MinutesPlayed(
                                player=player,
                                start_time=_start_time,
                                end_time=_start_time,
                                duration=end_time - _start_time,
                            )
                        )
                else:
                    for (
                        start_time,
                        end_time,
                        position,
                    ) in player.positions.ranges():
                        items.append(
                            MinutesPlayedPerPosition(
                                player=player,
                                position=position,
                                start_time=start_time,
                                end_time=end_time,
                                duration=end_time - start_time,
                            )
                        )

        return items
