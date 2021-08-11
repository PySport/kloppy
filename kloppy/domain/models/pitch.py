from dataclasses import dataclass
from enum import Enum
from math import sqrt
from typing import Optional


@dataclass
class Dimension:
    """
    Attributes:
        min: Minimal possible value within this dimension
        max: Maximal possible value within this dimension
    """

    min: float
    max: float

    def __eq__(self, other):
        if isinstance(self, Dimension):
            return self.min == other.min and self.max == other.max

        return False

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
    length: float = None
    width: float = None

    def __eq__(self, other):
        if isinstance(self, PitchDimensions):
            return self.x_dim == other.x_dim and self.y_dim == other.y_dim

        return False


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


@dataclass(frozen=True)
class Point3D(Point):
    """
    Point on the pitch that includes the z coordinate for height (e.g. of the ball).

    Attributes:
        z: z coordinate in unit of [`PitchDimensions`][kloppy.domain.models.pitch.PitchDimensions]
    """

    z: Optional[float]
