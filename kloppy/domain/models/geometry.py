from dataclasses import dataclass


@dataclass
class Scale(object):
    min: float
    max: float


@dataclass
class CoordinateSystem(object):
    x_scale: Scale
    y_scale: Scale
    x_to_meter: float
    y_to_meter: float


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Line(object):
    p1: Point
    p2: Point


@dataclass
class Rectangle(object):
    p1: Point
    p2: Point

