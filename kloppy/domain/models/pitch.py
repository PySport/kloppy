from dataclasses import dataclass

@dataclass
class Dimension:
    min: float
    max: float

    def to_base(self, value: float) -> float:
        return (value - self.min) / (self.max - self.min)

    def from_base(self, value: float) -> float:
        return value * (self.max - self.min) + self.min


@dataclass
class PitchDimensions:
    x_dim: Dimension
    y_dim: Dimension
    x_per_meter: float = None
    y_per_meter: float = None


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def distance_to_point(self, Point) -> int:
        # returns the euclidean distance between the point and another provided point
        return int(round(sum([(a - b)**2 for a, b in zip((self.x, self.y), (Point.x, Point.y))])**(1/2), 0))
