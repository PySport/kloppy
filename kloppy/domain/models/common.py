from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum, Flag
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

from kloppy.utils import deprecated, snake_case

if TYPE_CHECKING:
    from ..services.transformers.data_record import (
        Column,
        NamedColumns,
    )

from .position import PositionType

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

if sys.version_info >= (3, 11):
    from typing import Self, Unpack
else:
    from typing_extensions import Self, Unpack

from kloppy.exceptions import (
    InvalidFilterError,
    KloppyParameterError,
    OrientationError,
)

from .formation import FormationType
from .pitch import (
    DEFAULT_PITCH_LENGTH,
    DEFAULT_PITCH_WIDTH,
    Dimension,
    ImperialPitchDimensions,
    MetricPitchDimensions,
    NormalizedPitchDimensions,
    OptaPitchDimensions,
    PitchDimensions,
    Unit,
    WyscoutPitchDimensions,
)
from .time import Period, Time, TimeContainer


@dataclass
class Score:
    """
    The scoreline of a match.

    Attributes:
        home: Goals scored by the home team.
        away: Goals scored by the away team.
    """

    home: int
    away: int


class Ground(Enum):
    """
    Whether a team is playing at home or away.

    Attributes:
        HOME (Ground): The team is playing at home.
        AWAY (Ground): The team is playing away.
        REFEREE (Ground): Referee (could be used in tracking data).
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
    Data providers.

    Attributes:
        METRICA (Provider):
        TRACAB (Provider):
        SECONDSPECTRUM (Provider):
        OPTA (Provider):
        PFF (Provider):
        SKILLCORNER (Provider):
        STATSBOMB (Provider):
        SPORTEC (Provider):
        WYSCOUT (Provider):
        KLOPPY (Provider):
        DATAFACTORY (Provider):
        STATSPERFORM (Provider):
        SPORTVU (Provider):
        CDF (Provider):
        OTHER (Provider):
    """

    METRICA = "metrica"
    TRACAB = "tracab"
    SECONDSPECTRUM = "second_spectrum"
    OPTA = "opta"
    PFF = "pff"
    SKILLCORNER = "skillcorner"
    STATSBOMB = "statsbomb"
    SPORTEC = "sportec"
    WYSCOUT = "wyscout"
    KLOPPY = "kloppy"
    DATAFACTORY = "datafactory"
    STATSPERFORM = "statsperform"
    HAWKEYE = "hawkeye"
    SPORTVU = "sportvu"
    SIGNALITY = "signality"
    CDF = "common_data_format"
    OTHER = "other"

    def __str__(self):
        return self.value


class OfficialType(Enum):
    """Enumeration for types of officials (referees)."""

    VideoAssistantReferee = "Video Assistant Referee"
    AssistantVideoAssistantReferee = "Assistant Video Assistant Referee"
    MainReferee = "Main Referee"
    AssistantReferee = "Assistant Referee"
    FourthOfficial = "Fourth Official"
    Unknown = "Unknown"

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class Official:
    """
    Represents an official (referee) with optional names and roles.
    """

    official_id: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[OfficialType] = None

    @property
    def full_name(self):
        """
        Returns the full name of the official, falling back to role-based or ID-based naming.
        """
        if self.name:
            return self.name
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.last_name:
            return self.last_name
        if self.role:
            return f"{snake_case(str(self.role))}_{self.official_id}"
        return f"official_{self.official_id}"


@dataclass(frozen=True)
class Player:
    """
    A player in a team.

    Attributes:
        player_id (str): Identifier given by the provider.
        team (team): The player's team.
        jersey_no (int): The player's jersey number.
        first_name (str, optional): The player's first name.
        last_name (str, optional): The player's last name.
        name (str, optional): Full name of the player.
        full_name (str): If `name` is not set, this will be the concatenation
            of `first_name` and `last_name` or if these are also not set,
            the concatenation of the team's ground and the jersey number.
        starting (bool): `True` when player is part of the starting XI.
        starting_position (Position, optional): The player's starting position
            or `None` if the player is not starting.
        poisitions (TimeContainer[Position]): The player's positions over time.
        attributes (dict): Additional attributes given by the provider.
    """

    player_id: str
    team: "Team"
    jersey_no: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None

    # match specific
    starting: bool = False
    starting_position: Optional[PositionType] = None
    positions: TimeContainer[PositionType] = field(
        default_factory=TimeContainer, compare=False
    )

    attributes: Dict = field(default_factory=dict, compare=False)

    @property
    def full_name(self):
        if self.name:
            return self.name
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}"
        return f"{self.team.ground}_{self.jersey_no}"

    @property
    @deprecated("starting_position or positions should be used")
    def position(self) -> Optional[PositionType]:
        try:
            return self.positions.last()
        except KeyError:
            return None

    def __str__(self):
        return self.full_name

    def __hash__(self):
        return hash(self.player_id)

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.player_id == other.player_id

    def set_position(self, time: Time, position: Optional[PositionType]):
        self.positions.set(time, position)


@dataclass
class Team:
    """
    A team in a match.

    Attributes:
        team_id (str): Identifier given by the provider.
        name (str): Readable name of the team.
        ground (Ground): The team's ground (home or away).
        players (List[Player]): The team's players.
        starting_formation (FormationType, optional): The team's starting formation.
    """

    team_id: str
    name: str
    ground: Ground
    starting_formation: Optional[FormationType] = None
    formations: TimeContainer[FormationType] = field(
        default_factory=TimeContainer, compare=False
    )
    players: List[Player] = field(default_factory=list)

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.team_id)

    def __eq__(self, other):
        if not isinstance(other, Team):
            return False
        return self.team_id == other.team_id

    def get_player_by_jersey_number(self, jersey_no: int) -> Optional[Player]:
        """Get a player by their jersey number.

        Args:
            jersey_no (int): The jersey number of the player.

        Returns:
            Player: The player with the given jersey number or `None` if no
                    player with that jersey number is found.
        """
        jersey_no = int(jersey_no)
        for player in self.players:
            if player.jersey_no == jersey_no:
                return player

        return None

    def get_player_by_position(
        self, position: PositionType, time: Time
    ) -> Optional[Player]:
        """Get a player by their position at a given time.

        Args:
            position (PositionType): The position.
            time (Time): The time for which the position should be retrieved.

        Returns:
            Player: The player with the given position or `None` if no player
                    with that position is found.
        """
        for player in self.players:
            if player.positions.items:
                try:
                    player_position = player.positions.value_at(time)
                except KeyError:  # player that is subbed in later
                    continue
                if player_position and player_position == position:
                    return player

        return None

    def get_player_by_id(self, player_id: Union[int, str]) -> Optional[Player]:
        """Get a player by their identifier.

        Args:
            player_id (int or str): The identifier of the player.

        Returns:
            Player: The player with the given identifier or `None` if no player
                    with that identifier is found.
        """
        player_id = str(player_id)

        for player in self.players:
            if player.player_id == player_id:
                return player

        return None

    def set_formation(self, time: Time, formation: Optional[FormationType]):
        self.formations.set(time, formation)


class BallState(Enum):
    """
    Whether the ball is in play or not.

    Attributes:
        ALIVE (BallState): Ball is in play.
        DEAD (BallState): Ball is not in play.
    """

    ALIVE = "alive"
    DEAD = "dead"

    def __repr__(self):
        return self.value


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
    The direction of play for the home team.

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
    """
    The orientation of the y-axis in a [`CoordinateSystem`][kloppy.domain.CoordinateSystem].

    Attributes:
        TOP_TO_BOTTOM: The y coordinate increases from top to bottom of the pitch.
        BOTTOM_TO_TOP: The y coordinate decreases from top to bottom of the pitch.
    """

    TOP_TO_BOTTOM = "top-to-bottom"
    BOTTOM_TO_TOP = "bottom-to-top"


class Origin(Enum):
    """
    The location of the origin in a [`CoordinateSystem`][kloppy.domain.CoordinateSystem].

    Defines where the (0, 0) point is located on the field.

    Attributes:
        TOP_LEFT: Origin at the top left of the field
        BOTTOM_LEFT: Origin at the bottom left of the field
        CENTER: Origin at the center of the field
    """

    TOP_LEFT = "top-left"
    BOTTOM_LEFT = "bottom-left"
    CENTER = "center"

    def __str__(self):
        return self.value


class CoordinateSystem(ABC):
    """
    Base class for coordinate systems.

    A coordinate system defines how coordinates are represented in a dataset.

    Attributes:
        origin (Origin): The location of the origin.
        vertical_orientation (VerticalOrientation): The orientation of the y-axis.
        pitch_dimensions (PitchDimensions): The dimensions of the pitch.
        normalized (bool): Whether the pitch dimensions are normalized. This
            means that the coordinates are mapped to a fixed range, e.g. from
            0 to 1. In contrast, non-normalized coordinates correspond to the
            real-world dimensions of the pitch.
        pitch_length (float, optional): The real length of the pitch.
        pitch_width (float, optional): The real width of the pitch.
    """

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

    @property
    def pitch_length(self) -> Optional[float]:
        return self.pitch_dimensions.pitch_length

    @property
    def pitch_width(self) -> Optional[float]:
        return self.pitch_dimensions.pitch_width

    def __eq__(self, other):
        if isinstance(other, CoordinateSystem):
            return (
                self.origin == other.origin
                and self.vertical_orientation == other.vertical_orientation
                and self.pitch_dimensions == other.pitch_dimensions
            )

        return False

    def to_mplsoccer(self):
        """ "Convert the coordinate system to a mplsoccer BaseDims object.

        Example:
        >>> from kloppy.domain import KloppyCoordinateSystem
        >>> from mplsoccer import Pitch
        >>> coordinate_system = KloppyCoordinateSystem()
        >>> pitch = Pitch(dimensions=coordinate_system.to_mplsoccer())

        Note:
            This method is experimental and may change in the future.
        """
        try:
            from mplsoccer.dimensions import BaseDims
        except ImportError:
            raise ImportError(
                "Seems like you don't have `mplsoccer` installed. "
                "Please install it using: pip install mplsoccer"
            )

        if (
            self.pitch_dimensions.x_dim.min is None
            or self.pitch_dimensions.x_dim.max is None
        ):
            raise ValueError(
                "The x-dimensions of the pitch must be fully defined."
            )
        if (
            self.pitch_dimensions.y_dim.min is None
            or self.pitch_dimensions.y_dim.max is None
        ):
            raise ValueError(
                "The y-dimensions of the pitch must be fully defined."
            )

        pitch_length = (
            self.pitch_dimensions.pitch_length or DEFAULT_PITCH_LENGTH
        )
        pitch_width = self.pitch_dimensions.pitch_width or DEFAULT_PITCH_WIDTH

        invert_y = (
            self.vertical_orientation == VerticalOrientation.TOP_TO_BOTTOM
        )
        origin_center = self.origin == Origin.CENTER

        neg_if_inverted = -1 if invert_y else 1
        center = (0, 0)
        if self.origin == Origin.BOTTOM_LEFT:
            center = (
                (
                    self.pitch_dimensions.x_dim.max
                    - self.pitch_dimensions.x_dim.min
                )
                / 2,
                (
                    self.pitch_dimensions.y_dim.max
                    - self.pitch_dimensions.y_dim.min
                )
                / 2,
            )
        elif self.origin == Origin.TOP_LEFT:
            neg_if_inverted = -1
            center = (
                (
                    self.pitch_dimensions.x_dim.max
                    - self.pitch_dimensions.x_dim.min
                )
                / 2,
                (
                    self.pitch_dimensions.y_dim.max
                    - self.pitch_dimensions.y_dim.min
                )
                / 2,
            )

        dim = BaseDims(
            left=self.pitch_dimensions.x_dim.min,
            right=self.pitch_dimensions.x_dim.max,
            bottom=self.pitch_dimensions.y_dim.min
            if not invert_y
            else self.pitch_dimensions.y_dim.max,
            top=self.pitch_dimensions.y_dim.max
            if not invert_y
            else self.pitch_dimensions.y_dim.min,
            width=self.pitch_dimensions.x_dim.max
            - self.pitch_dimensions.x_dim.min,
            length=self.pitch_dimensions.y_dim.max
            - self.pitch_dimensions.y_dim.min,
            goal_bottom=center[1]
            - (neg_if_inverted / 2 * self.pitch_dimensions.goal_width),
            goal_top=center[1]
            + (neg_if_inverted / 2 * self.pitch_dimensions.goal_width),
            six_yard_left=self.pitch_dimensions.x_dim.min
            + self.pitch_dimensions.six_yard_length,
            six_yard_right=self.pitch_dimensions.x_dim.max
            - self.pitch_dimensions.six_yard_length,
            six_yard_bottom=center[1]
            - (neg_if_inverted / 2 * self.pitch_dimensions.six_yard_width),
            six_yard_top=center[1]
            + (neg_if_inverted / 2 * self.pitch_dimensions.six_yard_width),
            penalty_spot_distance=self.pitch_dimensions.penalty_spot_distance,
            penalty_left=self.pitch_dimensions.x_dim.min
            + self.pitch_dimensions.penalty_spot_distance,
            penalty_right=self.pitch_dimensions.x_dim.max
            - self.pitch_dimensions.penalty_spot_distance,
            penalty_area_left=self.pitch_dimensions.x_dim.min
            + self.pitch_dimensions.penalty_area_length,
            penalty_area_right=self.pitch_dimensions.x_dim.max
            - self.pitch_dimensions.penalty_area_length,
            penalty_area_bottom=center[1]
            - (neg_if_inverted / 2 * self.pitch_dimensions.penalty_area_width),
            penalty_area_top=center[1]
            + (neg_if_inverted / 2 * self.pitch_dimensions.penalty_area_width),
            center_width=center[1],
            center_length=center[0],
            goal_width=self.pitch_dimensions.goal_width,
            goal_length=self.pitch_dimensions.goal_height,
            six_yard_width=self.pitch_dimensions.six_yard_width,
            six_yard_length=self.pitch_dimensions.six_yard_length,
            penalty_area_width=self.pitch_dimensions.penalty_area_width,
            penalty_area_length=self.pitch_dimensions.penalty_area_length,
            circle_diameter=self.pitch_dimensions.circle_radius * 2,
            corner_diameter=self.pitch_dimensions.corner_radius * 2,
            arc=0,
            invert_y=invert_y,
            origin_center=origin_center,
            pad_default=0.02
            * (
                self.pitch_dimensions.x_dim.max
                - self.pitch_dimensions.x_dim.min
            ),
            pad_multiplier=1,
            aspect_equal=False
            if self.pitch_dimensions.unit == Unit.NORMED
            else True,
            pitch_width=pitch_width,
            pitch_length=pitch_length,
            aspect=pitch_width / pitch_length
            if self.pitch_dimensions.unit == Unit.NORMED
            else 1.0,
        )
        return dim


class ProviderCoordinateSystem(CoordinateSystem):
    def __init__(
        self,
        pitch_length: Optional[float] = None,
        pitch_width: Optional[float] = None,
    ):
        self._pitch_length = pitch_length
        self._pitch_width = pitch_width

    @property
    @abstractmethod
    def provider(self) -> Provider:
        raise NotImplementedError


class CustomCoordinateSystem(CoordinateSystem):
    def __init__(
        self,
        origin: Origin,
        vertical_orientation: VerticalOrientation,
        pitch_dimensions: PitchDimensions,
    ):
        self._origin = origin
        self._vertical_orientation = vertical_orientation
        self._pitch_dimensions = pitch_dimensions

    @property
    def origin(self) -> Origin:
        return self._origin

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return self._vertical_orientation

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return self._pitch_dimensions


class KloppyCoordinateSystem(ProviderCoordinateSystem):
    """
    Kloppy's default coordinate system.

    Uses a normalized pitch with the origin at the top left and the y-axis
    oriented from top to bottom. The coordinates range from 0 to 1.

    If no pitch length and width are provided, the default pitch dimensions
    are 105m x 68m.
    """

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
        if self._pitch_length is not None and self._pitch_width is not None:
            return NormalizedPitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class MetricaCoordinateSystem(KloppyCoordinateSystem):
    """
    Metrica coordinate system.

    Uses a normalized pitch with the origin at the top left and the y-axis
    oriented from top to bottom. The coordinates range from 0 to 1.

    If no pitch length and width are provided, the default pitch dimensions
    are 105m x 68m.

    Notes:
        The Metrica coordinate system is the same as the
        [`KloppyCoordinateSystem`][kloppy.domain.KloppyCoordinateSystem].
    """

    @property
    def provider(self) -> Provider:
        return Provider.METRICA


class TracabCoordinateSystem(ProviderCoordinateSystem):
    """
    Tracab coordinate system.

    Uses a pitch with the origin at the center and the y-axis oriented from
    bottom to top. The coordinates are in centimeters.
    """

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
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class SecondSpectrumCoordinateSystem(ProviderCoordinateSystem):
    """
    Second Spectrum coordinate system.

    Uses a pitch with the origin at the center and the y-axis oriented from
    bottom to top. The coordinates are in meters.
    """

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
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class OptaCoordinateSystem(ProviderCoordinateSystem):
    """
    Opta coordinate system.

    Uses a normalized pitch with the origin at the bottom left and the y-axis
    oriented from bottom to top. The coordinates range from 0 to 100.
    """

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
            pitch_length=self._pitch_length, pitch_width=self._pitch_width
        )


class SportecEventDataCoordinateSystem(ProviderCoordinateSystem):
    """
    Sportec event data coordinate system.

    Uses a pitch with the origin at the bottom left and the y-axis oriented
    from top to bottom. The coordinates are in meters.
    """

    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    @property
    def origin(self) -> Origin:
        return Origin.BOTTOM_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return MetricPitchDimensions(
            x_dim=Dimension(0, self._pitch_length),
            y_dim=Dimension(0, self._pitch_width),
            pitch_length=self._pitch_length,
            pitch_width=self._pitch_width,
            standardized=False,
        )


class SportecTrackingDataCoordinateSystem(ProviderCoordinateSystem):
    """
    Sportec tracking data coordinate system.

    Uses a pitch with the origin at the center and the y-axis oriented
    from bottom to top. The coordinates are in meters.
    """

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
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class StatsBombCoordinateSystem(ProviderCoordinateSystem):
    """
    StatsBomb coordinate system.

    Uses a normalized pitch with the origin at the top left and the y-axis
    oriented from top to bottom. The x-coordinates range from 0 to 120 and
    the y-coordinates range from 0 to 80.
    """

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
            pitch_length=self._pitch_length,
            pitch_width=self._pitch_width,
            standardized=True,
        )


class PFFCoordinateSystem(ProviderCoordinateSystem):
    """
    PFF coordinate system.

    Uses a pitch with the origin at the center and the y-axis oriented
    from bottom to top. The coordinates are in meters.
    """

    @property
    def provider(self) -> Provider:
        return Provider.PFF

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class WyscoutCoordinateSystem(ProviderCoordinateSystem):
    """
    Wyscout coordinate system.

    Uses a normalized pitch with the origin at the top left and the y-axis
    oriented from top to bottom. The coordinates range from 0 to 100.
    """

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
            pitch_length=self._pitch_length, pitch_width=self._pitch_width
        )


class SkillCornerCoordinateSystem(ProviderCoordinateSystem):
    """
    SkillCorner coordinate system.

    Uses a pitch with the origin at the center and the y-axis oriented
    from bottom to top. The coordinates are in meters.
    """

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
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class SignalityCoordinateSystem(ProviderCoordinateSystem):
    @property
    def provider(self) -> Provider:
        return Provider.SIGNALITY

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class DatafactoryCoordinateSystem(ProviderCoordinateSystem):
    """
    Datafactory coordinate system.

    Uses a normalized pitch with the origin at the top left and the y-axis
    oriented from top to bottom. The coordinates range from -1 to 1.
    """

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
        if self._pitch_length is not None and self._pitch_width is not None:
            return NormalizedPitchDimensions(
                x_dim=Dimension(-1, 1),
                y_dim=Dimension(-1, 1),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class SportVUCoordinateSystem(ProviderCoordinateSystem):
    """
    StatsPerform SportVU coordinate system.

    Uses a pitch with the origin at the top left and the y-axis oriented
    from top to bottom. The coordinates are in meters.
    """

    @property
    def provider(self) -> Provider:
        return Provider.SPORTVU

    @property
    def origin(self) -> Origin:
        return Origin.TOP_LEFT

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.TOP_TO_BOTTOM

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        return MetricPitchDimensions(
            x_dim=Dimension(0, self._pitch_length),
            y_dim=Dimension(0, self._pitch_width),
            pitch_length=self._pitch_length,
            pitch_width=self._pitch_width,
            standardized=False,
        )


class HawkEyeCoordinateSystem(ProviderCoordinateSystem):
    """
    HawkEye coordinate system.

    Uses a pitch with the origin at the center and the y-axis oriented
    from bottom to top. The coordinates are in meters.
    """

    @property
    def provider(self) -> Provider:
        return Provider.HAWKEYE

    @property
    def origin(self) -> Origin:
        return Origin.CENTER

    @property
    def vertical_orientation(self) -> VerticalOrientation:
        return VerticalOrientation.BOTTOM_TO_TOP

    @property
    def pitch_dimensions(self) -> PitchDimensions:
        if self._pitch_length is not None and self._pitch_width is not None:
            return MetricPitchDimensions(
                x_dim=Dimension(
                    -1 * self._pitch_length / 2, self._pitch_length / 2
                ),
                y_dim=Dimension(
                    -1 * self._pitch_width / 2, self._pitch_width / 2
                ),
                pitch_length=self._pitch_length,
                pitch_width=self._pitch_width,
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


class DatasetType(Enum):
    """
    Dataset types.

    Attributes:
        TRACKING (DatasetType): A dataset containing tracking data.
        EVENT (DatasetType): A dataset containing event data.
        CODE (DatasetType): A dataset containing SportsCode annotations.
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
        Provider.PFF: PFFCoordinateSystem,
        Provider.WYSCOUT: WyscoutCoordinateSystem,
        Provider.SKILLCORNER: SkillCornerCoordinateSystem,
        Provider.DATAFACTORY: DatafactoryCoordinateSystem,
        Provider.SECONDSPECTRUM: SecondSpectrumCoordinateSystem,
        Provider.HAWKEYE: HawkEyeCoordinateSystem,
        Provider.SPORTVU: SportVUCoordinateSystem,
        Provider.SIGNALITY: SignalityCoordinateSystem,
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
class Statistic(ABC):
    name: str = field(init=False)


@dataclass
class ScalarStatistic(Statistic):
    value: float


@dataclass
class ExpectedGoals(ScalarStatistic):
    """Expected goals"""

    def __post_init__(self):
        self.name = "xG"


@dataclass
class PostShotExpectedGoals(ScalarStatistic):
    """Post-shot expected goals"""

    def __post_init__(self):
        self.name = "PSxG"


@dataclass
class ActionValue(Statistic):
    """Action value"""

    name: str
    action_value_scoring_before: Optional[float] = field(default=None)
    action_value_scoring_after: Optional[float] = field(default=None)
    action_value_conceding_before: Optional[float] = field(default=None)
    action_value_conceding_after: Optional[float] = field(default=None)

    @property
    def offensive_value(self) -> Optional[float]:
        if (
            self.action_value_scoring_before is None
            or self.action_value_scoring_after is None
        ):
            return None
        return (
            self.action_value_scoring_after - self.action_value_scoring_before
        )

    @property
    def defensive_value(self) -> Optional[float]:
        if (
            self.action_value_conceding_before is None
            or self.action_value_conceding_after is None
        ):
            return None
        return (
            self.action_value_conceding_after
            - self.action_value_conceding_before
        )

    @property
    def value(self) -> Optional[float]:
        if self.offensive_value is None or self.defensive_value is None:
            return None
        return self.offensive_value - self.defensive_value


@dataclass
class DataRecord(ABC):
    """
    Base class for a data record in a dataset.

    Attributes:
        dataset: The dataset to which the record belongs.
        prev_record: The previous record in the dataset.
        next_record: The next record in the dataset.
        record_id: The unique identifier of the record. Given by the provider.
        period: The match period in which the observation occurred.
        timestamp: Timestamp of occurrence, relative to the period kick-off.
        time: The time of the observation. Combines `period` and `timestamp`.
        attacking_direction: The attacking direction of the home team.
        ball_owning_team: The team that had possession of the ball.
        ball_state: The state of the ball at the time of the observation.
    """

    dataset: Dataset = field(init=False)
    prev_record: Optional[Self] = field(init=False)
    next_record: Optional[Self] = field(init=False)
    period: Period
    timestamp: timedelta
    statistics: List[Statistic]
    ball_owning_team: Optional[Team]
    ball_state: Optional[BallState]

    @property
    @abstractmethod
    def record_id(self) -> Union[int, str]:
        pass

    @property
    def time(self) -> Time:
        return Time(period=self.period, timestamp=self.timestamp)

    def set_refs(
        self,
        dataset: Dataset,
        prev: Optional[Self],
        next_: Optional[Self],
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

    def matches(
        self, filter_: Optional[Union[str, Callable[[Self], bool]]]
    ) -> bool:
        if filter_ is None:
            return True
        elif callable(filter_):
            return filter_(self)
        else:
            raise InvalidFilterError()

    def prev(
        self, filter_: Optional[Union[str, Callable[[Self], bool]]] = None
    ) -> Optional[Self]:
        if self.prev_record:
            prev_record = self.prev_record
            while prev_record:
                if prev_record.matches(filter_):
                    return prev_record
                prev_record = prev_record.prev_record

    def next(
        self, filter_: Optional[Union[str, Callable[[Self], bool]]] = None
    ) -> Optional[Self]:
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
    Metadata for a dataset.

    Metadata is additional information about the dataset that is not part of
    the actual data. It includes information about the teams, the pitch
    dimensions, the orientation, the provider, and more.

    Attributes:
        game_id: Game id of the game from the provider.
        date: Date of the game.
        game_week: Game week (or match day) of the game. It can also be the stage
            (ex: "8th Finals"), if the game is happening during a cup or a play-off.
        periods: List of [`Period`][kloppy.domain.models.common.Period] entities.
        teams: `[home_team, away_team]`.
        coordinate_system: The coordinate system in which the data is provided.
        pitch_dimensions: The dimensions of the pitch.
        orientation: The attacking direction of each team.
        flags: Flags describing what optional data is available in the dataset.
        provider: The provider of the dataset.
        score: The final score of the match.
        frame_rate: The frame rate (in Hertz) at which the data was recorded.
            Only for tracking data.
        attributes: Additional metadata.
    """

    periods: List[Period]
    teams: List[Team]
    coordinate_system: CoordinateSystem
    pitch_dimensions: PitchDimensions
    orientation: Orientation
    flags: DatasetFlag
    provider: Provider
    score: Optional[Score] = None
    frame_rate: Optional[float] = None
    date: Optional[datetime] = None
    game_week: Optional[str] = None
    game_id: Optional[str] = None
    home_coach: Optional[str] = None
    away_coach: Optional[str] = None
    officials: Optional[List] = field(default_factory=list)
    attributes: Optional[Dict] = field(default_factory=dict, compare=False)

    def __post_init__(self):
        if self.coordinate_system is not None:
            # set the pitch dimensions from the coordinate system
            self.pitch_dimensions = self.coordinate_system.pitch_dimensions

        for i, period in enumerate(self.periods):
            period.set_refs(
                prev=self.periods[i - 1] if i > 0 else None,
                next_=(
                    self.periods[i + 1] if i + 1 < len(self.periods) else None
                ),
            )


T = TypeVar("T", bound="DataRecord")


@dataclass
class Dataset(ABC, Generic[T]):
    """
    Base class for datasets.

    A dataset describes specific aspects of what happened during a single
    match as a sequence of [`DataRecord`][kloppy.domain.DataRecord] entities.

    Attributes:
        dataset_type: The type of the dataset.
        records: List of records in the dataset.
        metadata: Metadata for the dataset.
    """

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
                next_=(
                    self.records[i + 1] if i + 1 < len(self.records) else None
                ),
            )

        self._init_player_positions()
        self._update_formations_and_positions()

    def _init_player_positions(self):
        start_of_match = self.metadata.periods[0].start_time
        for team in self.metadata.teams:
            for player in team.players:
                player.positions.reset()
                if player.starting:
                    player.set_position(
                        start_of_match,
                        player.starting_position or PositionType.unknown(),
                    )

    def _update_formations_and_positions(self):
        """Update player positions based on the events for example."""
        pass

    @property
    @abstractmethod
    def dataset_type(self) -> DatasetType:
        raise NotImplementedError

    @abstractmethod
    def to_pandas(
        self,
        record_converter: Optional[Callable[[T], Dict]] = None,
        additional_columns: Optional[NamedColumns] = None,
    ) -> "DataFrame":
        pass

    def transform(self, *args, **kwargs):
        """
        See [transform][kloppy.helpers.transform]
        """
        from kloppy.helpers import transform

        return transform(self, *args, **kwargs)

    def filter(self, filter_: Union[str, Callable[[T], bool]]):
        """
        Filter all records used `filter_`

        Args:
            filter_: The filter to be used to filter the records. It can be a
                callable that takes a record and returns a boolean, or a string
                representing a css-like selector.

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
    def from_dataset(cls, dataset: Dataset, mapper_fn: Callable[[Self], Self]):
        """
        Create a new Dataset from other dataset

        Arguments:
            mapper_fn:

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
        *columns: Unpack[tuple[Column]],
        as_list: Literal[True] = True,
        **named_columns: NamedColumns,
    ) -> List[Dict[str, Any]]:
        ...

    @overload
    def to_records(
        self,
        *columns: Unpack[tuple[Column]],
        as_list: Literal[False] = False,
        **named_columns: NamedColumns,
    ) -> Iterable[Dict[str, Any]]:
        ...

    def to_records(
        self,
        *columns: Unpack[tuple[Column]],
        as_list: bool = True,
        **named_columns: NamedColumns,
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
        *columns: Unpack[tuple[Column]],
        orient: Literal["list"] = "list",
        **named_columns: NamedColumns,
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
        *columns: Unpack[tuple[Column]],
        engine: Optional[
            Union[
                Literal["polars"],
                Literal["pandas"],
                Literal["pandas[pyarrow]"],
            ]
        ] = None,
        **named_columns: NamedColumns,
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
                self.to_dict(*columns, orient="list", **named_columns)
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

            return DataFrame.from_dict(
                self.to_dict(*columns, orient="list", **named_columns)
            )
        elif engine == "polars":
            try:
                from polars import from_dict
            except ImportError:
                raise ImportError(
                    "Seems like you don't have polars installed. Please"
                    " install it using: pip install polars"
                )

            return from_dict(
                self.to_dict(*columns, orient="list", **named_columns)
            )
        else:
            raise KloppyParameterError(f"Engine {engine} is not valid")

    def __repr__(self):
        return f"<{self.__class__.__name__} record_count={len(self.records)}>"

    __str__ = __repr__
