from dataclasses import dataclass
from math import sqrt


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

    @classmethod
    def default(cls):
        return cls(x_dim=Dimension(0, 1), y_dim=Dimension(0, 1))

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


@dataclass(frozen=True)
class Point3D(Point):
    """
    Point on the pitch that includes the z coordinate for height (e.g. of the ball).

    Attributes:
        z: z coordinate in unit of [`PitchDimensions`][kloppy.domain.models.pitch.PitchDimensions]
    """

    z: float
