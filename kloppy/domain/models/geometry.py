from collections import namedtuple
from dataclasses import dataclass


@dataclass
class Scale(object):
    min: float
    max: float

    def to_base(self, value: float) -> float:
        return (value - self.min) / (self.max - self.min)

    def from_base(self, value: float) -> float:
        return value * (self.max - self.min) + self.min


@dataclass
class CoordinateSystem(object):
    x_scale: Scale
    y_scale: Scale
    x_to_meter: float = None
    y_to_meter: float = None


@dataclass
class Point2:
    x: float
    y: float

Point = namedtuple("Point", "x y")


@dataclass
class Line(object):
    p1: Point
    p2: Point


@dataclass
class Rectangle(object):
    p1: Point
    p2: Point

