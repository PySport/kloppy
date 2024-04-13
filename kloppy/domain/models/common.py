import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum, Flag
from typing import (
    Dict,
    List,
    Optional,
    Callable,
    Union,
    Any,
    TypeVar,
    Generic,
    NewType,
    overload,
    Iterable,
)


if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from .pitch import (
    PitchDimensions,
    Unit,
    Point,
    Dimension,
    NormalizedPitchDimensions,
    MetricPitchDimensions,
    ImperialPitchDimensions,
    OptaPitchDimensions,
    WyscoutPitchDimensions,
)
from .formation import FormationType
from ...exceptions import (
    OrientationError,
    InvalidFilterError,
    KloppyParameterError,
    KloppyError,
)


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
        SECONDSPECTRUM:
        OPTA:
        SKILLCORNER:
        STATSBOMB:
        SPORTEC:
        WYSCOUT:
        KLOPPY:
        DATAFACTORY:
        STATSPERFORM:
        SPORTVU:
    """

    METRICA = "metrica"
    TRACAB = "tracab"
    SECONDSPECTRUM = "second_spectrum"
    OPTA = "opta"
    SKILLCORNER = "skillcorner"
    STATSBOMB = "statsbomb"
    SPORTEC = "sportec"
    WYSCOUT = "wyscout"
    KLOPPY = "kloppy"
    DATAFACTORY = "datafactory"
    STATSPERFORM = "statsperform"
    SPORTVU = "sportvu"
    OTHER = "other"

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class Position:
    position_id: str
    name: str
    coordinates: Optional[Point] = None

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
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}"
        return f"{self.team.ground}_{self.jersey_no}"

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
        starting_formation: See ['FormationType']
    """

    team_id: str
    name: str
    ground: Ground
    starting_formation: Optional[FormationType] = None
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

    def get_player_by_position(self, position_id: Union[int, str]):
        position_id = str(position_id)
        for player in self.players:
            if player.position and player.position.position_id == position_id:
                return player

        return None

    def get_player_by_id(self, player_id: Union[int, str]):
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


@dataclass
class Period:
    """
    Period

    Attributes:
        id: `1` for first half, `2` for second half, `3` for first half of
            overtime, `4` for second half of overtime, `5` for penalty shootout
        start_timestamp: The UTC datetime of the kick-off or, if the
            absolute datetime is not available, the offset between the start
            of the data feed and the period's kick-off
        end_timestamp: The UTC datetime of the final whistle or, if the
            absolute datetime is not available, the offset between the start
            of the data feed and the period's final whistle
        attacking_direction: See [`AttackingDirection`][kloppy.domain.models.common.AttackingDirection]
    """

    id: int
    start_timestamp: Union[datetime, timedelta]
    end_timestamp: Union[datetime, timedelta]

    def contains(self, timestamp: datetime):
        if isinstance(self.start_timestamp, datetime) and isinstance(
            self.end_timestamp, datetime
        ):
            return self.start_timestamp <= timestamp <= self.end_timestamp
        raise KloppyError(
            "This method can only be used when start_timestamp and end_timestamp are a datetime"
        )

    @property
    def duration(self) -> timedelta:
        return self.end_timestamp - self.start_timestamp

    def __eq__(self, other):
        return isinstance(other, Period) and other.id == self.id


class Orientation(Enum):
    """
    The attacking direction of each team in a dataset.

    Attributes:
        BALL_OWNING_TEAM: The team that is currently in possession of the ball
            plays from left to right.
        ACTION_EXECUTING_TEAM: The team that executes the action
            plays from left to right. Used in event stream data only. Equivalent
            to "BALL_OWNING_TEAM" for tracking data.
        HOME_AWAY: The home team plays from left to right in the first period.
            The away team plays from left to right in the second period.
        AWAY_HOME: The away team plays from left to right in the first period.
            The home team plays from left to right in the second period.
        STATIC_HOME_AWAY: The home team plays from left to right in both periods.
        STATIC_AWAY_HOME: The away team plays from left to right in both periods.
        NOT_SET: The attacking direction is not defined.

    Notes:
        The attacking direction is not defined for penalty shootouts in the
        `HOME_AWAY`, `AWAY_HOME`, `STATIC_HOME_AWAY`, and `STATIC_AWAY_HOME`
        orientations. This period is ignored in orientation transforms
        involving one of these orientations and keeps its original
        attacking direction.
    """

    # change when possession changes
    BALL_OWNING_TEAM = "ball-owning-team"

    # depends on team which executed the action
    ACTION_EXECUTING_TEAM = "action-executing-team"

    # changes during half-time
    HOME_AWAY = "home-away"
    AWAY_HOME = "away-home"

    # won't change during match
    STATIC_HOME_AWAY = "fixed-home-away"
    STATIC_AWAY_HOME = "fixed-away-home"

    # Not set in dataset
    NOT_SET = "not-set"

    def __repr__(self):
        return self.value


class AttackingDirection(Enum):
    """
    AttackingDirection

    Attributes:
        LTR (AttackingDirection): Home team is playing from left to right
        RTL (AttackingDirection): Home team is playing from right to left
        NOT_SET (AttackingDirection): not set yet
    """

    LTR = "left-to-right"
    RTL = "right-to-left"
    NOT_SET = "not-set"

    @staticmethod
    def from_orientation(
        orientation: Orientation,
        period: Optional[Period] = None,
        ball_owning_team: Optional[Team] = None,
        action_executing_team: Optional[Team] = None,
    ) -> "AttackingDirection":
        """Determines the attacking direction for a specific data record.

        Args:
            orientation: The orientation of the dataset.
            period: The period of the data record.
            ball_owning_team: The team that is in possession of the ball.
            action_executing_team: The team that executes the action.

        Raises:
            OrientationError: If the attacking direction cannot be determined
                from the given data.

        Returns:
            The attacking direction for the given data record.
        """
        if orientation == Orientation.STATIC_HOME_AWAY:
            return AttackingDirection.LTR
        if orientation == Orientation.STATIC_AWAY_HOME:
            return AttackingDirection.RTL
        if orientation == Orientation.HOME_AWAY:
            if period is None:
                raise OrientationError(
                    "You must provide a period to determine the attacking direction"
                )
            dirmap = {
                1: AttackingDirection.LTR,
                2: AttackingDirection.RTL,
                3: AttackingDirection.LTR,
                4: AttackingDirection.RTL,
            }
            if period.id in dirmap:
                return dirmap[period.id]
            raise OrientationError(
                "This orientation is not defined for period %s" % period.id
            )
        if orientation == Orientation.AWAY_HOME:
            if period is None:
                raise OrientationError(
                    "You must provide a period to determine the attacking direction"
                )
            dirmap = {
                1: AttackingDirection.RTL,
                2: AttackingDirection.LTR,
                3: AttackingDirection.RTL,
                4: AttackingDirection.LTR,
            }
            if period.id in dirmap:
                return dirmap[period.id]
            raise OrientationError(
                "This orientation is not defined for period %s" % period.id
            )
        if orientation == Orientation.BALL_OWNING_TEAM:
            if ball_owning_team is None:
                raise OrientationError(
                    "You must provide the ball owning team to determine the attacking direction"
                )
            if ball_owning_team is not None:
                if ball_owning_team.ground == Ground.HOME:
                    return AttackingDirection.LTR
                if ball_owning_team.ground == Ground.AWAY:
                    return AttackingDirection.RTL
                raise OrientationError(
                    "Invalid ball_owning_team: %s", ball_owning_team
                )
            return AttackingDirection.NOT_SET
        if orientation == Orientation.ACTION_EXECUTING_TEAM:
            if action_executing_team is None:
                raise ValueError(
                    "You must provide the action executing team to determine the attacking direction"
                )
            if action_executing_team.ground == Ground.HOME:
                return AttackingDirection.LTR
            if action_executing_team.ground == Ground.AWAY:
                return AttackingDirection.RTL
            raise OrientationError(
                "Invalid action_executing_team: %s", action_executing_team
            )
        raise OrientationError("Unknown orientation: %s", orientation)

    def __repr__(self):
        return self.value


class VerticalOrientation(Enum):
    # the y axis increases as you go from top to bottom of the pitch
    TOP_TO_BOTTOM = "top-to-bottom"

    # the y axis decreases as you go from top to bottom of the pitch
    BOTTOM_TO_TOP = "bottom-to-top"


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
    pitch_length: Optional[float] = None
    pitch_width: Optional[float] = None

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

    @property
    def normalized(self) -> bool:
        return isinstance(self.pitch_dimensions, NormalizedPitchDimensions)


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
        if self.pitch_length is not None and self.pitch_width is not None:
            return NormalizedPitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1),
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                standardized=False,
            )
        else:
            return NormalizedPitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1),
                pitch_length=105,
                pitch_width=68,
                standardized=True,
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
        if self.pitch_length is not None and self.pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self.pitch_length / 2, self.pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self.pitch_width / 2, self.pitch_width / 2
                ),
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                standardized=False,
            ).convert(to_unit=Unit.CENTIMETERS)
        else:
            return MetricPitchDimensions(
                x_dim=Dimension(None, None),
                y_dim=Dimension(None, None),
                pitch_length=None,
                pitch_width=None,
                standardized=False,
            ).convert(to_unit=Unit.CENTIMETERS)


@dataclass
class SecondSpectrumCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.SECONDSPECTRUM

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        if self.pitch_length is not None and self.pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self.pitch_length / 2, self.pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self.pitch_width / 2, self.pitch_width / 2
                ),
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                standardized=False,
            )
        else:
            return MetricPitchDimensions(
                x_dim=Dimension(None, None),
                y_dim=Dimension(None, None),
                pitch_length=None,
                pitch_width=None,
                standardized=False,
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
        return OptaPitchDimensions(
            pitch_length=self.pitch_length, pitch_width=self.pitch_width
        )


@dataclass
class SportecEventDataCoordinateSystem(CoordinateSystem):
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
        return MetricPitchDimensions(
            x_dim=Dimension(0, self.pitch_length),
            y_dim=Dimension(0, self.pitch_width),
            pitch_length=self.pitch_length,
            pitch_width=self.pitch_width,
            standardized=False,
        )


@dataclass
class SportecTrackingDataCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        if self.pitch_length is not None and self.pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self.pitch_length / 2, self.pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self.pitch_width / 2, self.pitch_width / 2
                ),
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                standardized=False,
            )
        else:
            return MetricPitchDimensions(
                x_dim=Dimension(None, None),
                y_dim=Dimension(None, None),
                pitch_length=None,
                pitch_width=None,
                standardized=False,
            )


@dataclass
class StatsBombCoordinateSystem(CoordinateSystem):
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
        return ImperialPitchDimensions(
            x_dim=Dimension(0, 120),
            y_dim=Dimension(0, 80),
            pitch_length=self.pitch_length,
            pitch_width=self.pitch_width,
            standardized=True,
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
        return WyscoutPitchDimensions(
            pitch_length=self.pitch_length, pitch_width=self.pitch_width
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
        if self.pitch_length is not None and self.pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self.pitch_length / 2, self.pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self.pitch_width / 2, self.pitch_width / 2
                ),
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                standardized=False,
            )
        else:
            return MetricPitchDimensions(
                x_dim=Dimension(None, None),
                y_dim=Dimension(None, None),
                pitch_length=None,
                pitch_width=None,
                standardized=False,
            )


@dataclass
class DatafactoryCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.DATAFACTORY

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.TOP_TO_BOTTOM

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        if self.pitch_length is not None and self.pitch_width is not None:
            return NormalizedPitchDimensions(
                x_dim=Dimension(-1, 1),
                y_dim=Dimension(-1, 1),
                pitch_length=self.pitch_length,
                pitch_width=self.pitch_width,
                standardized=False,
            )
        else:
            return NormalizedPitchDimensions(
                x_dim=Dimension(-1, 1),
                y_dim=Dimension(-1, 1),
                pitch_length=105,
                pitch_width=68,
                standardized=True,
            )


@dataclass
class SportVUCoordinateSystem(CoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTVU

    @property
    def origin(self) -> Origin:
        return Origin.BOTTOM_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return MetricPitchDimensions(
            x_dim=Dimension(0, self.pitch_length),
            y_dim=Dimension(0, self.pitch_width),
            pitch_length=self.pitch_length,
            pitch_width=self.pitch_width,
            standardized=False,
        )


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


def build_coordinate_system(
    provider: Provider,
    dataset_type: DatasetType = DatasetType.EVENT,
    pitch_length: Optional[float] = None,
    pitch_width: Optional[float] = None,
) -> CoordinateSystem:
    """Build a coordinate system for a given provider and dataset type.

    Args:
        provider: The provider of the dataset.
        dataset_type: The type of the dataset.
        pitch_length: The real length of the pitch.
        pitch_width: The real width of the pitch.

    Returns:
        The coordinate system for the given provider and dataset type.
    """
    coordinate_systems = {
        Provider.TRACAB: TracabCoordinateSystem,
        Provider.KLOPPY: KloppyCoordinateSystem,
        Provider.METRICA: MetricaCoordinateSystem,
        Provider.OPTA: OptaCoordinateSystem,
        Provider.SPORTEC: {
            DatasetType.EVENT: SportecEventDataCoordinateSystem,
            DatasetType.TRACKING: SportecTrackingDataCoordinateSystem,
        },
        Provider.STATSBOMB: StatsBombCoordinateSystem,
        Provider.WYSCOUT: WyscoutCoordinateSystem,
        Provider.SKILLCORNER: SkillCornerCoordinateSystem,
        Provider.DATAFACTORY: DatafactoryCoordinateSystem,
        Provider.SECONDSPECTRUM: SecondSpectrumCoordinateSystem,
        Provider.SPORTVU: SportVUCoordinateSystem,
    }

    if provider in coordinate_systems:
        if isinstance(coordinate_systems[provider], dict):
            assert dataset_type in coordinate_systems[provider]
            return coordinate_systems[provider][dataset_type](
                pitch_length=pitch_length, pitch_width=pitch_width
            )
        else:
            return coordinate_systems[provider](
                pitch_length=pitch_length, pitch_width=pitch_width
            )
    else:
        raise ValueError(f"Invalid provider: {provider}")


class DatasetFlag(Flag):
    BALL_OWNING_TEAM = 1
    BALL_STATE = 2


@dataclass
class DataRecord(ABC):
    """
    DataRecord

    Attributes:
        period: See [`Period`][kloppy.domain.models.common.Period]
        timestamp: Timestamp of occurrence, relative to the period kick-off
        ball_owning_team: See [`Team`][kloppy.domain.models.common.Team]
        ball_state: See [`Team`][kloppy.domain.models.common.BallState]
    """

    dataset: "Dataset" = field(init=False)
    prev_record: Optional["DataRecord"] = field(init=False)
    next_record: Optional["DataRecord"] = field(init=False)
    period: Period
    timestamp: timedelta
    ball_owning_team: Optional[Team]
    ball_state: Optional[BallState]

    @property
    @abstractmethod
    def record_id(self) -> Union[int, str]:
        pass

    def set_refs(
        self,
        dataset: "Dataset",
        prev: Optional["DataRecord"],
        next_: Optional["DataRecord"],
    ):
        if hasattr(self, "dataset"):
            # TODO: determine if next/prev record should be affected
            # by Dataset.filter
            return

        self.dataset = dataset
        self.prev_record = prev
        self.next_record = next_

    @property
    def attacking_direction(self):
        if (
            self.dataset
            and self.dataset.metadata
            and self.dataset.metadata.orientation is not None
        ):
            try:
                return AttackingDirection.from_orientation(
                    self.dataset.metadata.orientation,
                    period=self.period,
                    ball_owning_team=self.ball_owning_team,
                )
            except OrientationError:
                return AttackingDirection.NOT_SET
        return AttackingDirection.NOT_SET

    def matches(self, filter_) -> bool:
        if filter_ is None:
            return True
        elif callable(filter_):
            return filter_(self)
        else:
            raise InvalidFilterError()

    def prev(self, filter_=None) -> Optional[Self]:
        if self.prev_record:
            prev_record = self.prev_record
            while prev_record:
                if prev_record.matches(filter_):
                    return prev_record
                prev_record = prev_record.prev_record

    def next(self, filter_=None) -> Optional[Self]:
        if self.next_record:
            next_record = self.next_record
            while next_record:
                if next_record.matches(filter_):
                    return next_record
                next_record = next_record.next_record

    def replace(self, **changes):
        return replace(self, **changes)

    def __str__(self):
        return f"<{self.__class__.__name__}>"

    __repr__ = __str__


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
    orientation: Orientation
    flags: DatasetFlag
    provider: Provider
    coordinate_system: CoordinateSystem
    score: Optional[Score] = None
    frame_rate: Optional[float] = None
    attributes: Optional[Dict] = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if self.coordinate_system is not None:
            # set the pitch dimensions from the coordinate system
            self.pitch_dimensions = self.coordinate_system.pitch_dimensions


T = TypeVar("T", bound="DataRecord")


@dataclass
class Dataset(ABC, Generic[T]):
    """
    Dataset

    Attributes:
        records:
        metadata: Metadata for this Dataset

    """

    Column = NewType("Column", Union[str, Callable[[T], Any]])

    records: List[T]
    metadata: Metadata

    def __iter__(self):
        return iter(self.records)

    def __getitem__(self, item):
        return self.records[item]

    def __len__(self):
        return len(self.records)

    def __post_init__(self):
        for i, record in enumerate(self.records):
            record.set_refs(
                dataset=self,
                prev=self.records[i - 1] if i > 0 else None,
                next_=self.records[i + 1]
                if i + 1 < len(self.records)
                else None,
            )

    @property
    @abstractmethod
    def dataset_type(self) -> DatasetType:
        raise NotImplementedError

    @abstractmethod
    def to_pandas(
        self,
        record_converter: Callable[[T], Dict] = None,
        additional_columns: Dict[str, Union[Callable[[T], Any], Any]] = None,
    ) -> "DataFrame":
        pass

    def transform(self, *args, **kwargs):
        """
        See [transform][kloppy.helpers.transform]
        """
        from kloppy.helpers import transform

        return transform(self, *args, **kwargs)

    def filter(self, filter_):
        """
        Filter all records used `filter_`

        Arguments:
            - filter_:

        Examples:
            >>> from kloppy.domain import EventType
            >>> dataset = dataset.filter(lambda event: event.event_type == EventType.PASS)
            >>> dataset = dataset.filter('pass')
        """
        return replace(
            self,
            records=self.find_all(filter_),
        )

    def map(self, mapper):
        return replace(
            self, records=[mapper(record) for record in self.records]
        )

    def find_all(self, filter_) -> List[T]:
        return [record for record in self.records if record.matches(filter_)]

    def find(self, filter_) -> Optional[T]:
        for record in self.records:
            if record.matches(filter_):
                return record

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

    def get_record_by_id(self, record_id: Union[int, str]) -> Optional[T]:
        for record in self.records:
            if record.record_id == record_id:
                return record

    @overload
    def to_records(
        self,
        *columns: "Column",
        as_list: Literal[True] = True,
        **named_columns: "Column",
    ) -> List[Dict[str, Any]]:
        ...

    @overload
    def to_records(
        self,
        *columns: "Column",
        as_list: Literal[False] = False,
        **named_columns: "Column",
    ) -> Iterable[Dict[str, Any]]:
        ...

    def to_records(
        self,
        *columns: "Column",
        as_list: bool = True,
        **named_columns: "Column",
    ) -> Union[List[Dict[str, Any]], Iterable[Dict[str, Any]]]:
        from ..services.transformers.data_record import get_transformer_cls

        transformer = get_transformer_cls(self.dataset_type)(
            *columns, **named_columns
        )
        iterator = map(transformer, self.records)
        if as_list:
            return list(iterator)
        else:
            return iterator

    def to_dict(
        self,
        *columns: "Column",
        orient: Literal["list"] = "list",
        **named_columns: "Column",
    ) -> Dict[str, List[Any]]:
        if orient == "list":
            from ..services.transformers.data_record import get_transformer_cls

            transformer = get_transformer_cls(self.dataset_type)(
                *columns, **named_columns
            )

            c = len(self.records)
            items = defaultdict(lambda: [None] * c)
            for i, record in enumerate(self.records):
                item = transformer(record)
                for k, v in item.items():
                    items[k][i] = v

            return items
        else:
            raise KloppyParameterError(
                f"Orient {orient} is not supported. Only orient='list' is supported"
            )

    def to_df(
        self,
        *columns: "Column",
        engine: Optional[
            Union[
                Literal["polars"],
                Literal["pandas"],
                Literal["pandas[pyarrow]"],
            ]
        ] = None,
        **named_columns: "Column",
    ):
        from kloppy.config import get_config

        if not engine:
            engine = get_config("dataframe.engine")

        if engine == "pandas[pyarrow]":
            try:
                import pandas as pd

                types_mapper = pd.ArrowDtype
            except ImportError:
                raise ImportError(
                    "Seems like you don't have pandas installed. Please"
                    " install it using: pip install pandas"
                )
            except AttributeError:
                raise AttributeError(
                    "Seems like you have an older version of pandas installed. Please"
                    " upgrade to at least 1.5 using: pip install pandas>=1.5"
                )

            try:
                import pyarrow as pa
            except ImportError:
                raise ImportError(
                    "Seems like you don't have pyarrow installed. Please"
                    " install it using: pip install pyarrow"
                )

            table = pa.Table.from_pydict(
                self.to_dict(*columns, **named_columns)
            )
            return table.to_pandas(types_mapper=types_mapper)

        elif engine == "pandas":
            try:
                from pandas import DataFrame
            except ImportError:
                raise ImportError(
                    "Seems like you don't have pandas installed. Please"
                    " install it using: pip install pandas"
                )

            return DataFrame.from_dict(self.to_dict(*columns, **named_columns))
        elif engine == "polars":
            try:
                from polars import from_dict
            except ImportError:
                raise ImportError(
                    "Seems like you don't have polars installed. Please"
                    " install it using: pip install polars"
                )

            return from_dict(self.to_dict(*columns, **named_columns))
        else:
            raise KloppyParameterError(f"Engine {engine} is not valid")

    def __repr__(self):
        return f"<{self.__class__.__name__} record_count={len(self.records)}>"

    __str__ = __repr__
