from dataclasses import dataclass
from datetime import timedelta
from typing import List, NamedTuple, Optional, Dict, Tuple, Union
from enum import Enum

from kloppy.domain import (
    EventDataset,
    Player,
    Team,
    Time,
    PositionType,
    BallState,
    FoulCommittedEvent,
    PassResult,
    SubstitutionEvent,
    CardEvent,
    PlayerOnEvent,
    PlayerOffEvent,
    Period,
    GenericEvent,
    ShotResult,
    InterceptionResult,
    TakeOnResult,
    BallOutEvent,
    SetPieceQualifier,
)
from kloppy.domain.services.aggregators.aggregator import (
    EventDatasetAggregator,
)


class BreakdownKey(Enum):
    POSITION = "position"
    POSSESSION_STATE = "possession_state"


class PossessionState(Enum):
    IN_POSSESSION = "in-possession"
    OUT_OF_POSSESSION = "out-of-possession"
    BALL_DEAD = "ball-dead"


EVENTS_CAUSING_DEAD_BALL = (
    FoulCommittedEvent,
    SubstitutionEvent,
    CardEvent,
    PlayerOnEvent,
    PlayerOffEvent,
    BallOutEvent,
)

RESULTS_CAUSING_DEAD_BALL = (
    PassResult.OFFSIDE,
    ShotResult.GOAL,
    ShotResult.OWN_GOAL,
    ShotResult.OFF_TARGET,
    PassResult.OUT,
    InterceptionResult.OUT,
    TakeOnResult.OUT,
)


@dataclass(frozen=True)
class MinutesPlayedKey:
    player: Optional[Player] = None
    team: Optional[Team] = None
    position: Optional[PositionType] = None
    possession_state: Optional[PossessionState] = None

    def __post_init__(self):
        if (self.player is None and self.team is None) or (
            self.player is not None and self.team is not None
        ):
            raise ValueError(
                "Either 'player' or 'team' must be provided, but not both."
            )


class MinutesPlayed(NamedTuple):
    key: MinutesPlayedKey
    start_time: Time
    end_time: Time
    duration: timedelta


class MinutesPlayedAggregator(EventDatasetAggregator):
    def __init__(self, breakdown_key: Optional[Union[BreakdownKey, str]] = None):
        if isinstance(breakdown_key, str):
            try:
                breakdown_key = BreakdownKey(breakdown_key)
            except ValueError:
                raise ValueError(
                    f"BreakdownKey {breakdown_key} not found. Known keys: {', '.join(key.value for key in BreakdownKey)}")
            self.breakdown_key = breakdown_key

    @staticmethod
    def get_possession_state(
        ball_state: BallState, ball_owning_team: Team, team: Team
    ):
        if ball_state == BallState.DEAD or ball_owning_team is None:
            return PossessionState.BALL_DEAD
        return (
            PossessionState.IN_POSSESSION
            if ball_owning_team == team
            else PossessionState.OUT_OF_POSSESSION
        )

    @staticmethod
    def _flip_possession_state(
        state: PossessionState, flip: bool
    ) -> PossessionState:
        if flip:
            if state == PossessionState.IN_POSSESSION:
                return PossessionState.OUT_OF_POSSESSION
            elif state == PossessionState.OUT_OF_POSSESSION:
                return PossessionState.IN_POSSESSION
        return state

    @staticmethod
    def _handle_possession_state_end(
        time_per_possession_state: Dict[PossessionState, timedelta],
        time_per_player: Dict[Player, Dict[PossessionState, timedelta]],
        players_start_end_times: Dict[Player, Tuple[Time, Time, bool]],
        start_time: Time,
        end_time: Time,
        ball_state: BallState,
        ball_owning_team: Team,
        first_team: Team,
    ):
        possession_state = MinutesPlayedAggregator.get_possession_state(
            ball_state, ball_owning_team, first_team
        )
        time_per_possession_state[possession_state] += end_time - start_time
        MinutesPlayedAggregator._accumulate_player_time(
            time_per_player,
            players_start_end_times,
            start_time,
            end_time,
            possession_state,
        )

    @staticmethod
    def _accumulate_player_time(
        time_per_player: Dict[Player, Dict[PossessionState, timedelta]],
        players_start_end_times: Dict[Player, Tuple[Time, Time, bool]],
        start_time: Time,
        end_time: Time,
        possession_state: PossessionState,
    ):
        for player, (
            start_player_time,
            end_player_time,
            _,
        ) in players_start_end_times.items():
            if start_player_time <= end_time and end_player_time >= start_time:
                duration = min(end_time, end_player_time) - max(
                    start_time, start_player_time
                )
                time_per_player[player][possession_state] += duration

    def aggregate(self, dataset: EventDataset) -> List[MinutesPlayed]:

        items = []

        if self.breakdown_key == BreakdownKey.POSITION:
            for team in dataset.metadata.teams:
                for player in team.players:
                    for (
                        start_timestamp,
                        end_time,
                        position,
                    ) in player.positions.ranges():
                        items.append(
                            MinutesPlayed(
                                key=MinutesPlayedKey(
                                    player=player, position=position
                                ),
                                start_time=start_timestamp,
                                end_time=end_time,
                                duration=end_time - start_timestamp,
                            )
                        )
        elif self.breakdown_key == BreakdownKey.POSSESSION_STATE:
            first_team = dataset.metadata.teams[0]

            players_start_end_times = {}
            for team in dataset.metadata.teams:
                for player in team.players:
                    _start_time = None
                    end_time = None
                    for (
                        start_timestamp,
                        end_time,
                        position,
                    ) in player.positions.ranges():
                        if not _start_time:
                            _start_time = start_timestamp

                    if _start_time:
                        flip_possession_state = team != first_team
                        players_start_end_times[player] = (
                            _start_time,
                            end_time,
                            flip_possession_state,
                        )
            time_per_possession_state = {
                state: timedelta(0) for state in PossessionState
            }
            time_per_player = {
                player: {state: timedelta(0) for state in PossessionState}
                for player in players_start_end_times.keys()
            }
            start_time: Optional[Time] = dataset.metadata.periods[0].start_time
            ball_owning_team: Optional[Team] = None
            ball_state: Optional[BallState] = None
            period: Optional[Period] = dataset.metadata.periods[0]

            for event in dataset.events:
                if isinstance(event, GenericEvent):
                    continue
                if event.time < start_time:
                    continue

                if (
                    any(
                        isinstance(q, SetPieceQualifier)
                        for q in event.qualifiers or []
                    )
                    and ball_state != BallState.DEAD
                ):
                    # Ball state should be dead, so we mistagged a prior event (for example a clearance that went out of play)
                    previous_event = event.prev(
                        lambda x: not isinstance(x, GenericEvent)
                    )
                    if previous_event:
                        self._handle_possession_state_end(
                            time_per_possession_state,
                            time_per_player,
                            players_start_end_times,
                            start_time,
                            previous_event.time,
                            ball_state,
                            ball_owning_team,
                            first_team,
                        )
                        start_time = previous_event.time
                        ball_state = (
                            BallState.DEAD
                        )  # set current bal state to dead
                        ball_owning_team = event.ball_owning_team

                actual_event_ball_state = (
                    BallState.DEAD
                    if isinstance(event, EVENTS_CAUSING_DEAD_BALL)
                    or (event.result in RESULTS_CAUSING_DEAD_BALL)
                    else event.ball_state
                )

                if (
                    actual_event_ball_state == BallState.DEAD
                    and event.result in RESULTS_CAUSING_DEAD_BALL
                ):

                    _actual_event_timestamp = (
                        event.receive_timestamp
                        if hasattr(event, "receive_timestamp")
                        and event.receive_timestamp is not None
                        else event.end_timestamp
                        if hasattr(event, "end_timestamp")
                        and event.end_timestamp is not None
                        else event.timestamp
                    )
                    actual_event_time = Time(
                        event.period, _actual_event_timestamp
                    )
                else:
                    actual_event_time = event.time
                if event.period != period:

                    end_time = Time(
                        period=period,
                        timestamp=(
                            period.end_timestamp - period.start_timestamp
                        ),
                    )
                    self._handle_possession_state_end(
                        time_per_possession_state,
                        time_per_player,
                        players_start_end_times,
                        start_time,
                        end_time,
                        ball_state,
                        ball_owning_team,
                        first_team,
                    )

                    start_time = actual_event_time
                    period = event.period
                    ball_state = actual_event_ball_state
                    ball_owning_team = event.ball_owning_team

                if (
                    actual_event_ball_state != ball_state
                    or event.ball_owning_team != ball_owning_team
                ):

                    self._handle_possession_state_end(
                        time_per_possession_state,
                        time_per_player,
                        players_start_end_times,
                        start_time,
                        actual_event_time,
                        ball_state,
                        ball_owning_team,
                        first_team,
                    )

                    start_time = actual_event_time
                    ball_state = actual_event_ball_state
                    ball_owning_team = event.ball_owning_team

            # Handle the last event in the period
            end_time = Time(
                period=period,
                timestamp=(period.end_timestamp - period.start_timestamp),
            )
            self._handle_possession_state_end(
                time_per_possession_state,
                time_per_player,
                players_start_end_times,
                start_time,
                end_time,
                ball_state,
                ball_owning_team,
                first_team,
            )

            for team in dataset.metadata.teams:
                flip_possession = team != first_team
                for state, duration in time_per_possession_state.items():
                    possession_state = self._flip_possession_state(
                        state, flip_possession
                    )

                    items.append(
                        MinutesPlayed(
                            key=MinutesPlayedKey(
                                team=team, possession_state=possession_state
                            ),
                            start_time=dataset.metadata.periods[0].start_time,
                            end_time=dataset.metadata.periods[1].end_time,
                            duration=duration,
                        )
                    )
                for player in team.players:
                    if player in time_per_player:
                        for state, duration in time_per_player[player].items():
                            possession_state = self._flip_possession_state(
                                state, flip_possession
                            )
                            items.append(
                                MinutesPlayed(
                                    key=MinutesPlayedKey(
                                        player=player,
                                        possession_state=possession_state,
                                    ),
                                    start_time=dataset.metadata.periods[
                                        0
                                    ].start_time,
                                    end_time=dataset.metadata.periods[
                                        1
                                    ].end_time,
                                    duration=duration,
                                )
                            )
        else:
            _start_time = dataset.metadata.periods[0].start_time
            _end_time = dataset.metadata.periods[1].end_time
            for team in dataset.metadata.teams:
                items.append(
                    MinutesPlayed(
                        key=MinutesPlayedKey(team=team),
                        start_time=_start_time,
                        end_time=_end_time,
                        duration=_end_time - _start_time,
                    )
                )
                for player in team.players:
                    _start_time = None
                    end_time = None
                    for (
                        start_timestamp,
                        end_time,
                        position,
                    ) in player.positions.ranges():
                        if not _start_time:
                            _start_time = start_timestamp

                    if _start_time:
                        items.append(
                            MinutesPlayed(
                                key=MinutesPlayedKey(player=player),
                                start_time=_start_time,
                                end_time=end_time,
                                duration=end_time - _start_time,
                            )
                        )

        return items
