from dataclasses import dataclass
from enum import Enum
from math import sqrt

from kloppy.domain import Provider, VerticalOrientation


@dataclass
class Dimension:
    """
    Attributes:
        min: Minimal possible value within this dimension
        max: Maximal possible value within this dimension
    """

    min: float
    max: float

    def to_base(self, value: float) -> float:
        return (value - self.min) / (self.max - self.min)

    def from_base(self, value: float) -> float:
        return value * (self.max - self.min) + self.min


@dataclass
class PitchDimensions:
    """
    Attributes:
        x_dim: See [`Dimension`][kloppy.domain.models.pitch.Dimension]
        y_dim: See [`Dimension`][kloppy.domain.models.pitch.Dimension]
        x_per_meter: number of units per meter in the x dimension
        y_per_meter: number of units per meter in the y dimension
    """

    x_dim: Dimension
    y_dim: Dimension
    x_per_meter: float = None
    y_per_meter: float = None

    @property
    def length(self) -> float:
        """
        Calculates the length of the pitch in meters if possible.
        """
        return (
            (self.x_dim.max - self.x_dim.min) / self.x_per_meter
            if self.x_per_meter
            else None
        )

    @property
    def width(self) -> float:
        """
        Calculates the width of the pitch in meters if possible.
        """
        return (
            (self.y_dim.max - self.y_dim.min) / self.y_per_meter
            if self.y_per_meter
            else None
        )


@dataclass(frozen=True)
class Point:
    """
    Point on the pitch.

    Attributes:
        x: x coordinate in unit of [`PitchDimensions`][kloppy.domain.models.pitch.PitchDimensions]
        y: y coordinate in unit of [`PitchDimensions`][kloppy.domain.models.pitch.PitchDimensions]
    """

    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        """
        Calculates the euclidean distance between the point and another provided point

        Arguments:
            other: See [`Point`][kloppy.domain.models.pitch.Point]
        """
        return sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class Origin(Enum):
    """
    Attributes:
        TOP_LEFT: Origin at the top left of the field
        BOTTOM_RIGHT: Origin at the bottom left of the field
        CENTER: Origin at the center of the field
    """

    TOP_LEFT = "top-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"

    def __str__(self):
        return self.value


@dataclass
class CoordinateSystem:
    provider: Provider
    origin: Origin
    vertical_orientation: VerticalOrientation
    normalized: bool
    pitch_dimensions: PitchDimensions


@dataclass(frozen=True)
class KloppyCoordinateSystem(CoordinateSystem):
    provider: None
    origin: Origin.TOP_LEFT
    vertical_orientation: VerticalOrientation.TOP_TO_BOTTOM
    normalized: True
    pitch_dimensions: None


@dataclass(frozen=True)
class TracabCoordinateSystem(CoordinateSystem):
    provider: Provider.TRACAB
    origin: Origin.CENTER
    vertical_orientation: VerticalOrientation.BOTTOM_TO_TOP
    normalized: False
    pitch_dimensions: None
