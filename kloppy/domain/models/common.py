from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from enum import Enum, Flag
from typing import Dict, List, Optional, Callable, Union, Any

from .pitch import PitchDimensions, Point


@dataclass
class Score:
    """
    Score

    Attributes:
        home:
        away:
    """

    home: int
    away: int


class Ground(Enum):
    """
    Attributes:
        HOME: home playing team
        AWAY: away playing team
        REFEREE: Referee (could be used in tracking data)
    """

    HOME = "home"
    AWAY = "away"
    REFEREE = "referee"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class Provider(Enum):
    """
    Attributes:
        METRICA:
        TRACAB:
        OPTA:
        SKILLCORNER:
        STATSBOMB:
        SPORTEC:
        WYSCOUT:
    """

    METRICA = "metrica"
    TRACAB = "tracab"
    OPTA = "opta"
    SKILLCORNER = "skillcorner"
    STATSBOMB = "statsbomb"
    SPORTEC = "sportec"
    WYSCOUT = "wyscout"
    OTHER = "other"

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
    """
    Attributes:
        player_id: identifier given by the provider
        team: See [`Team`][kloppy.domain.models.common.Team]
        jersey_no: Jersey number
        name: Full name of the player
        first_name: First name
        last_name: Last name
        starting: `True` when player is part of the starting 11
        position: See [`Position][kloppy.domain.models.common.Position]
        attributes: attributes given by the provider
    """

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
    """

    Attributes:
        team_id: id of the team, given by the provider
        name: readable name of the team
        ground: See [`Ground`][kloppy.domain.models.common.Ground]
        players: See [`Player`][kloppy.domain.models.common.Player]
    """

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
    """
    BallState

    Attributes:
        ALIVE (BallState): Ball is in play
        DEAD (BallState): Ball is not in play
    """

    ALIVE = "alive"
    DEAD = "dead"

    def __repr__(self):
        return self.value


class AttackingDirection(Enum):
    """
    AttackingDirection

    Attributes:
        HOME_AWAY (AttackingDirection): Home team is playing from left to right
        AWAY_HOME (AttackingDirection): Home team is playing from right to left
        NOT_SET (AttackingDirection): not set yet
    """

    HOME_AWAY = "home-away"
    AWAY_HOME = "away-home"
    NOT_SET = "not-set"

    def __repr__(self):
        return self.value


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

    # Not set in dataset
    NOT_SET = "not-set"

    def get_orientation_factor(
        self,
        attacking_direction: AttackingDirection,
        ball_owning_team: Team,
        action_executing_team: Team,
    ) -> int:
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

    def __repr__(self):
        return self.value


@dataclass
class Period:
    """
    Period

    Attributes:
        id: `1` for first half, `2` for second half
        start_timestamp: timestamp given by provider (can be unix timestamp or relative)
        end_timestamp: timestamp given by provider (can be unix timestamp or relative)
        attacking_direction: See [`AttackingDirection`][kloppy.domain.models.common.AttackingDirection]
    """

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

    def __eq__(self, other):
        return isinstance(other, Period) and other.id == self.id


class DatasetFlag(Flag):
    BALL_OWNING_TEAM = 1
    BALL_STATE = 2


@dataclass
class DataRecord(ABC):
    """
    DataRecord

    Attributes:
        period: See [`Period`][kloppy.domain.models.common.Period]
        timestamp: Timestamp of occurrence
        ball_owning_team: See [`Team`][kloppy.domain.models.common.Team]
        ball_state: See [`Team`][kloppy.domain.models.common.BallState]
    """

    period: Period
    timestamp: float
    ball_owning_team: Optional[Team]
    ball_state: Optional[BallState]


@dataclass
class Metadata:
    """
    Metadata

    Attributes:
        teams: `[home_team, away_team]`. See [`Team`][kloppy.domain.models.common.Team]
        periods: See [`Period`][kloppy.domain.models.common.Period]
        pitch_dimensions: See [`PitchDimensions`][kloppy.domain.models.pitch.PitchDimensions]
        score: See [`Score`][kloppy.domain.models.common.Score]
        frame_rate:
        orientation: See [`Orientation`][kloppy.domain.models.common.Orientation]
        flags:
        provider: See [`Provider`][kloppy.domain.models.common.Provider]
    """

    teams: List[Team]
    periods: List[Period]
    pitch_dimensions: PitchDimensions
    score: Score
    frame_rate: float
    orientation: Orientation
    flags: DatasetFlag
    provider: Provider


class DatasetType(Enum):
    """
    DatasetType

    Attributes:
        TRACKING (DatasetType):
        EVENT (DatasetType):
        CODE (DatasetType):
    """

    TRACKING = "TRACKING"
    EVENT = "EVENT"
    CODE = "CODE"

    def __repr__(self):
        return self.value


@dataclass
class Dataset(ABC):
    """
    Dataset

    Attributes:
        records:
        metadata: Metadata for this Dataset

    """

    records: List[DataRecord]
    metadata: Metadata

    @property
    @abstractmethod
    def dataset_type(self) -> DatasetType:
        raise NotImplementedError

    def to_pandas(self, *args, **kwargs):
        """
        See [to_pandas][kloppy.helpers.to_pandas]
        """
        from kloppy import to_pandas

        return to_pandas(
            self,
            *args,
            **kwargs,
        )

    def transform(self, *args, **kwargs):
        """
        See [transform][kloppy.helpers.transform]
        """
        from kloppy import transform

        return transform(self, *args, **kwargs)

    def filter(self, filter_fn: Callable[[DataRecord], bool]):
        """
        Filter all records used `filter_fn`

        Arguments:
            - filter_fn:

        Examples:
            >>> from kloppy.domain import EventType
            >>> dataset = dataset.filter(lambda event: event.event_type == EventType.PASS)
        """
        return replace(
            self,
            records=[record for record in self.records if filter_fn(record)],
        )

    @classmethod
    def from_dataset(
        cls, dataset: "Dataset", mapper_fn: Callable[[DataRecord], DataRecord]
    ):
        """
        Create a new Dataset from other dataset

        Arguments:
            - mapper_fn:

        Examples:
            >>> from kloppy.domain import Code,     CodeDataset

            >>> code_dataset = (
            >>>     CodeDataset
            >>>     .from_dataset(
            >>>         dataset,
            >>>         lambda event: Code(
            >>>             code_id=event.event_id,
            >>>             code=event.event_name,
            >>>             period=event.period,
            >>>             timestamp=event.timestamp - 7,
            >>>             end_timestamp=event.timestamp + 5,
            >>>             labels={
            >>>                 'Player': str(event.player),
            >>>                 'Team': str(event.team)
            >>>             }
            >>>         )
            >>>     )
            >>> )
        """
        return cls(
            metadata=dataset.metadata,
            records=[mapper_fn(record) for record in dataset.records],
        )
