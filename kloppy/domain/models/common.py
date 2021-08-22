from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from enum import Enum, Flag
from typing import Dict, List, Optional, Callable, Union, Any

from .pitch import PitchDimensions, Point, Dimension


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
        KLOPPY:
    """

    METRICA = "metrica"
    TRACAB = "tracab"
    OPTA = "opta"
    SKILLCORNER = "skillcorner"
    STATSBOMB = "statsbomb"
    SPORTEC = "sportec"
    WYSCOUT = "wyscout"
    KLOPPY = "kloppy"
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


class VerticalOrientation(Enum):
    # the y axis increases as you go from top to bottom of the pitch
    TOP_TO_BOTTOM = "top-to-bottom"

    # the y axis decreases as you go from top to bottom of the pitch
    BOTTOM_TO_TOP = "bottom-to-top"


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


class Origin(Enum):
    """
    Attributes:
        TOP_LEFT: Origin at the top left of the field
        BOTTOM_RIGHT: Origin at the bottom left of the field
        CENTER: Origin at the center of the field
    """

    TOP_LEFT = "top-left"
    BOTTOM_LEFT = "bottom-left"
    CENTER = "center"

    def __str__(self):
        return self.value


@dataclass
class CoordinateSystem(ABC):
    normalized: bool
    length: float = None
    width: float = None

    def __eq__(self, other):
        if isinstance(other, CoordinateSystem):
            return (
                self.origin == other.origin
                and self.vertical_orientation == other.vertical_orientation
                and self.pitch_dimensions == other.pitch_dimensions
            )

        return False

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError

    @property
    @abstractmethod
    def origin(self) -> Origin:
        raise NotImplementedError

    @property
    @abstractmethod
    def vertical_orientation(self) -> VerticalOrientation:
        raise NotImplementedError

    @property
    @abstractmethod
    def pitch_dimensions(self) -> PitchDimensions:
        raise NotImplementedError


@dataclass
class KloppyCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.KLOPPY

    @property
    def origin(self) -> Origin:
        return Origin.TOP_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.TOP_TO_BOTTOM

    @property
    def pitch_dimensions(self) -> PitchDimensions:

        if self.length is not None and self.width is not None:
            return PitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1),
                length=self.length,
                width=self.width,
            )
        else:
            return PitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1),
            )


@dataclass
class MetricaCoordinateSystem(KloppyCoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.METRICA


@dataclass
class TracabCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.TRACAB

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return PitchDimensions(
            x_dim=Dimension(-1 * self.length * 100 / 2, self.length * 100 / 2),
            y_dim=Dimension(-1 * self.width * 100 / 2, self.width * 100 / 2),
            length=self.length,
            width=self.width,
        )


@dataclass
class OptaCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.OPTA

    @property
    def origin(self) -> Origin:
        return Origin.BOTTOM_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return PitchDimensions(
            x_dim=Dimension(0, 100),
            y_dim=Dimension(0, 100),
        )


@dataclass
class SportecCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    @property
    def origin(self) -> Origin:
        return Origin.BOTTOM_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.TOP_TO_BOTTOM

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return PitchDimensions(
            x_dim=Dimension(0, self.length),
            y_dim=Dimension(0, self.width),
            length=self.length,
            width=self.width,
        )


@dataclass
class StatsbombCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.STATSBOMB

    @property
    def origin(self) -> Origin:
        return Origin.TOP_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.TOP_TO_BOTTOM

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return PitchDimensions(
            x_dim=Dimension(0, 120),
            y_dim=Dimension(0, 80),
        )


class WyscoutCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.WYSCOUT

    @property
    def origin(self) -> Origin:
        return Origin.TOP_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.TOP_TO_BOTTOM

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return PitchDimensions(
            x_dim=Dimension(0, 100),
            y_dim=Dimension(0, 100),
        )


@dataclass
class SkillCornerCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.SKILLCORNER

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return PitchDimensions(
            x_dim=Dimension(-1 * self.length / 2, self.length / 2),
            y_dim=Dimension(-1 * self.width / 2, self.width / 2),
            length=self.length,
            width=self.width,
        )


def build_coordinate_system(provider: Provider, **kwargs):

    if provider == Provider.TRACAB:
        return TracabCoordinateSystem(normalized=False, **kwargs)

    if provider == Provider.KLOPPY:
        return KloppyCoordinateSystem(normalized=True, **kwargs)

    if provider == Provider.METRICA:
        return MetricaCoordinateSystem(normalized=True, **kwargs)

    if provider == Provider.OPTA:
        return OptaCoordinateSystem(normalized=False, **kwargs)

    if provider == Provider.SPORTEC:
        return SportecCoordinateSystem(normalized=False, **kwargs)

    if provider == Provider.STATSBOMB:
        return StatsbombCoordinateSystem(normalized=False, **kwargs)

    if provider == Provider.WYSCOUT:
        return WyscoutCoordinateSystem(normalized=False, **kwargs)

    if provider == Provider.SKILLCORNER:
        return SkillCornerCoordinateSystem(normalized=False, **kwargs)


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
    coordinate_system: CoordinateSystem


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
