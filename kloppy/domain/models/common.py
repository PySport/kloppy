from abc import ABC
from dataclasses import dataclass
from enum import Enum, Flag
from typing import Optional, List

from .pitch import PitchDimensions


class Team(Enum):
    HOME = "home"
    AWAY = "away"


class BallState(Enum):
    ALIVE = "alive"
    DEAD = "dead"


class AttackingDirection(Enum):
    HOME_AWAY = "home-away"  # home L -> R, away R -> L
    AWAY_HOME = "away-home"  # home R -> L, away L -> R
    NOT_SET = "not-set"  # not set yet


class Orientation(Enum):
    # change when possession changes
    BALL_OWNING_TEAM = "ball-owning-team"

    # changes during half-time
    HOME_TEAM = "home-team"
    AWAY_TEAM = "away-team"

    # won't change during match
    FIXED_HOME_AWAY = "fixed-home-away"
    FIXED_AWAY_HOME = "fixed-away-home"

    def get_orientation_factor(self,
                               attacking_direction: AttackingDirection,
                               ball_owning_team: Team):
        if self == Orientation.FIXED_HOME_AWAY:
            return -1
        elif self == Orientation.FIXED_AWAY_HOME:
            return 1
        elif self == Orientation.HOME_TEAM:
            if attacking_direction == AttackingDirection.HOME_AWAY:
                return -1
            else:
                return 1
        elif self == Orientation.AWAY_TEAM:
            if attacking_direction == AttackingDirection.AWAY_HOME:
                return -1
            else:
                return 1
        elif self == Orientation.BALL_OWNING_TEAM:
            if ((ball_owning_team == Team.HOME
                 and attacking_direction == AttackingDirection.HOME_AWAY)
                    or
                    (ball_owning_team == Team.AWAY
                     and attacking_direction == AttackingDirection.AWAY_HOME)):
                return -1
            else:
                return 1


@dataclass
class Period:
    id: int
    start_timestamp: float
    end_timestamp: float
    attacking_direction: Optional[AttackingDirection] = AttackingDirection.NOT_SET

    def contains(self, timestamp: float):
        return self.start_timestamp <= timestamp <= self.end_timestamp

    @property
    def attacking_direction_set(self):
        return self.attacking_direction != AttackingDirection.NOT_SET

    def set_attacking_direction(self, attacking_direction: AttackingDirection):
        self.attacking_direction = attacking_direction


class DataSetFlag(Flag):
    BALL_OWNING_TEAM = 1
    BALL_STATE = 2


@dataclass
class DataRecord(ABC):
    timestamp: float
    ball_owning_team: Team
    ball_state: BallState

    period: Period


@dataclass
class DataSet(ABC):
    flags: DataSetFlag
    pitch_dimensions: PitchDimensions
    orientation: Orientation
    periods: List[Period]
    records: List[DataRecord]


