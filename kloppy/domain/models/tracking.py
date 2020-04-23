from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict

from .pitch import (
    PitchDimensions,
    Point
)


class Player(object):
    jersey_no: str
    position: Point


class BallOwningTeam(Enum):
    HOME = 0
    AWAY = 1

    @classmethod
    def from_string(cls, string):
        if string == "H":
            return cls.HOME
        elif string == "A":
            return cls.AWAY
        else:
            raise Exception(u"Unknown ball owning team: {}".format(string))


class BallState(Enum):
    ALIVE = "alive"
    DEAD = "dead"

    @classmethod
    def from_string(cls, string):
        if string == "Alive":
            return cls.ALIVE
        elif string == "Dead":
            return cls.DEAD
        else:
            raise Exception(u"Unknown ball state: {}".format(string))


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

    @staticmethod
    def get_orientation_factor(orientation: 'Orientation',
                               attacking_direction: AttackingDirection,
                               ball_owning_team: BallOwningTeam):
        if orientation == Orientation.FIXED_HOME_AWAY:
            return -1
        elif orientation == Orientation.FIXED_AWAY_HOME:
            return 1
        elif orientation == Orientation.HOME_TEAM:
            if attacking_direction == AttackingDirection.HOME_AWAY:
                return -1
            else:
                return 1
        elif orientation == Orientation.AWAY_TEAM:
            if attacking_direction == AttackingDirection.AWAY_HOME:
                return -1
            else:
                return 1
        elif orientation == Orientation.BALL_OWNING_TEAM:
            if ((ball_owning_team == BallOwningTeam.HOME
                 and attacking_direction == AttackingDirection.HOME_AWAY)
                    or
                    (ball_owning_team == BallOwningTeam.AWAY
                     and attacking_direction == AttackingDirection.AWAY_HOME)):
                return -1
            else:
                return 1


@dataclass
class Period(object):
    id: int
    start_frame_id: int
    end_frame_id: int
    attacking_direction: Optional[AttackingDirection] = AttackingDirection.NOT_SET

    @property
    def frame_count(self):
        return self.end_frame_id - self.start_frame_id

    def contains(self, frame_id: int):
        return self.start_frame_id <= frame_id <= self.end_frame_id

    @property
    def attacking_direction_set(self):
        return self.attacking_direction != AttackingDirection.NOT_SET

    def set_attacking_direction(self, attacking_direction: AttackingDirection):
        self.attacking_direction = attacking_direction


@dataclass
class Frame(object):
    frame_id: int
    ball_owning_team: BallOwningTeam
    ball_state: BallState

    period: Period

    home_team_player_positions: Dict[str, Point]
    away_team_player_positions: Dict[str, Point]
    ball_position: Point


@dataclass
class DataSet(object):
    pitch_dimensions: PitchDimensions
    orientation: Orientation

    frame_rate: int
    periods: List[Period]
    frames: List[Frame]
