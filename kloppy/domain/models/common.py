from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from enum import Enum, Flag
from typing import Optional, List, Dict

from .pitch import PitchDimensions, Point


@dataclass
class Score:
    home: int
    away: int


class Ground(Enum):
    HOME = "home"
    AWAY = "away"
    REFEREE = "referee"

    def __str__(self):
        return self.value


class Provider(Enum):
    METRICA = "metrica"
    TRACAB = "tracab"
    OPTA = "opta"
    STATSBOMB = "statsbomb"
    SPORTEC = "sportec"

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class Position:
    position_id: str
    name: str
    coordinates: Point

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class Player:
    player_id: str
    team: "Team"
    jersey_no: int
    name: str = None
    first_name: str = None
    last_name: str = None

    # match specific
    starting: bool = None
    position: Position = None

    attributes: Optional[Dict] = field(default_factory=dict, compare=False)

    @property
    def full_name(self):
        if self.name:
            return self.name
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name

    def __hash__(self):
        return hash(self.player_id)

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.player_id == other.player_id


@dataclass
class Team:
    team_id: str
    name: str
    ground: Ground
    players: List[Player] = field(default_factory=list)

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.team_id)

    def __eq__(self, other):
        if not isinstance(other, Team):
            return False
        return self.team_id == other.team_id

    def get_player_by_jersey_number(self, jersey_no: int):
        jersey_no = int(jersey_no)
        for player in self.players:
            if player.jersey_no == jersey_no:
                return player

        return None

    def get_player_by_id(self, player_id: str):
        player_id = str(player_id)

        for player in self.players:
            if player.player_id == player_id:
                return player

        return None


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

    # depends on team which executed the action
    ACTION_EXECUTING_TEAM = "action-executing-team"

    # changes during half-time
    HOME_TEAM = "home-team"
    AWAY_TEAM = "away-team"

    # won't change during match
    FIXED_HOME_AWAY = "fixed-home-away"
    FIXED_AWAY_HOME = "fixed-away-home"

    def get_orientation_factor(
        self,
        attacking_direction: AttackingDirection,
        ball_owning_team: Team,
        action_executing_team: Team,
    ):
        if self == Orientation.FIXED_HOME_AWAY:
            return -1
        elif self == Orientation.FIXED_AWAY_HOME:
            return 1
        elif self == Orientation.HOME_TEAM:
            if attacking_direction == AttackingDirection.HOME_AWAY:
                return -1
            elif attacking_direction == AttackingDirection.AWAY_HOME:
                return 1
            else:
                raise Exception("AttackingDirection not set")
        elif self == Orientation.AWAY_TEAM:
            if attacking_direction == AttackingDirection.AWAY_HOME:
                return -1
            elif attacking_direction == AttackingDirection.HOME_AWAY:
                return 1
            else:
                raise Exception("AttackingDirection not set")
        elif self == Orientation.BALL_OWNING_TEAM:
            if ball_owning_team.ground == Ground.HOME:
                return -1
            elif ball_owning_team.ground == Ground.AWAY:
                return 1
            else:
                raise Exception(
                    f"Invalid ball_owning_team: {ball_owning_team}"
                )
        elif self == Orientation.ACTION_EXECUTING_TEAM:
            if action_executing_team.ground == Ground.HOME:
                return -1
            elif action_executing_team.ground == Ground.AWAY:
                return 1
            else:
                raise Exception(
                    f"Invalid action_executing_team: {action_executing_team}"
                )
        else:
            raise Exception(f"Unknown orientation: {self}")


@dataclass
class Period:
    id: int
    start_timestamp: float
    end_timestamp: float
    attacking_direction: Optional[
        AttackingDirection
    ] = AttackingDirection.NOT_SET

    def contains(self, timestamp: float):
        return self.start_timestamp <= timestamp <= self.end_timestamp

    @property
    def attacking_direction_set(self):
        return self.attacking_direction != AttackingDirection.NOT_SET

    def set_attacking_direction(self, attacking_direction: AttackingDirection):
        self.attacking_direction = attacking_direction

    @property
    def duration(self):
        return self.end_timestamp - self.start_timestamp


class DatasetFlag(Flag):
    BALL_OWNING_TEAM = 1
    BALL_STATE = 2


@dataclass
class DataRecord(ABC):
    period: Period
    timestamp: float
    ball_owning_team: Team
    ball_state: BallState


@dataclass
class Metadata:
    teams: List[Team]
    periods: List[Period]
    pitch_dimensions: PitchDimensions
    score: Score
    frame_rate: float
    orientation: Orientation
    flags: DatasetFlag
    provider: Provider


class DatasetType(Enum):
    TRACKING = "TRACKING"
    EVENT = "EVENT"


@dataclass
class Dataset(ABC):
    records: List[DataRecord]
    metadata: Metadata

    @property
    @abstractmethod
    def dataset_type(self) -> DatasetType:
        raise NotImplementedError

    def to_pandas(self, *args, **kwargs):
        from kloppy import to_pandas

        return to_pandas(self, *args, **kwargs)

    def transform(self, *args, **kwargs):
        from kloppy import transform

        return transform(self, *args, **kwargs)

    def filter(self, filter_fn):
        return replace(
            self,
            records=[record for record in self.records if filter_fn(record)],
        )
