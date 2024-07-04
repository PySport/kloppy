import warnings
from dataclasses import dataclass
from enum import Enum
from math import sqrt
from typing import Optional

from kloppy.exceptions import MissingDimensionError

DEFAULT_PITCH_LENGTH = 105.0
DEFAULT_PITCH_WIDTH = 68.0


class Unit(Enum):
    """Unit to measure distances on a pitch."""

    METERS = "m"
    YARDS = "y"
    CENTIMETERS = "cm"
    FEET = "ft"
    NORMED = "normed"

    def convert(self, to_unit: "Unit", value: float) -> float:
        """Converts a value from one unit to another.

        Arguments:
            to_unit: The unit to convert to
            value: The value to convert
        Returns:
            The value converted to the target unit
        """
        conversion_factors = {
            (Unit.METERS, Unit.METERS): 1,
            (Unit.METERS, Unit.YARDS): 1.09361,
            (Unit.METERS, Unit.CENTIMETERS): 100,
            (Unit.METERS, Unit.FEET): 3.281,
        }
        if self == to_unit:
            return value
        elif self == Unit.NORMED or to_unit == Unit.NORMED:
            raise ValueError("Cannot convert to or from a normed unit")

        factor_to_meter = conversion_factors.get((Unit.METERS, self))
        factor_from_meter = conversion_factors.get((Unit.METERS, to_unit))
        assert (
            factor_to_meter is not None
        ), f"Conversion factor for {self} is not defined"
        assert (
            factor_from_meter is not None
        ), f"Conversion factor for {to_unit} is not defined"
        return value / factor_to_meter * factor_from_meter


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


@dataclass(frozen=True)
class Dimension:
    """Limits of pitch boundaries along a single axis.

    Attributes:
        min: Minimal possible value within this dimension
        max: Maximal possible value within this dimension
    """

    min: Optional[float] = None
    max: Optional[float] = None

    def to_base(self, value: float) -> float:
        """Map a value from this dimension to [0, 1]."""
        if self.min is None or self.max is None:
            raise MissingDimensionError()
        return (value - self.min) / (self.max - self.min)

    def from_base(self, value: float) -> float:
        """Map a value from [0, 1] to this dimension."""
        if self.min is None or self.max is None:
            raise MissingDimensionError()
        return value * (self.max - self.min) + self.min


@dataclass
class PitchDimensions:
    """Specifies the dimensions of a pitch.

    Attributes:
        x_dim: Limits of pitch boundaries in longitudinal direction.
            See [`Dimension`][kloppy.domain.models.pitch.Dimension]
        y_dim: Limits of pitch boundaries in lateral direction.
            See [`Dimension`][kloppy.domain.models.pitch.Dimension]
        standardized: Used to denote standardized pitch dimensions where data
            is scaled along the axes independent of the actual dimensions of
            the pitch. To get non-distored calculations, the `length` and
            `width` of the pitch need to be specified.
        unit: The unit in which distances are measured along the axes of the pitch.
        goal_width: Width of the goal.
        goal_height: Height of the goal.
        six_yard_width: Width of the six yard box.
        six_yard_length: Length of the six yard box.
        penalty_area_width: Width of the penalty area.
        penalty_area_length: Length of the penalty area.
        circle_radius: Radius of the center circle (in the longitudinal direction).
        corner_radius: Radius of the corner arcs.
        penalty_spot_distance: Distance from the goal line to the penalty spot.
        penalty_arc_radius: Radius of the penalty arc (in the longitudinal direction).
        pitch_length: True length of the pitch, in meters.
        pitch_width: True width of the pitch, in meters.
    """

    x_dim: Dimension
    y_dim: Dimension
    standardized: bool
    unit: Unit

    goal_width: float
    goal_height: Optional[float]
    six_yard_width: float
    six_yard_length: float
    penalty_area_width: float
    penalty_area_length: float
    circle_radius: float
    corner_radius: float
    penalty_spot_distance: float
    penalty_arc_radius: float

    pitch_length: Optional[float] = None
    pitch_width: Optional[float] = None

    def convert(self, to_unit: Unit) -> "PitchDimensions":
        """Convert the pitch dimensions to another unit.

        Arguments:
            to_unit: The unit to convert to

        Returns:
            The pitch dimensions in the target unit
        """
        return PitchDimensions(
            x_dim=Dimension(
                min=self.unit.convert(to_unit, self.x_dim.min)
                if self.x_dim.min is not None
                else None,
                max=self.unit.convert(to_unit, self.x_dim.max)
                if self.x_dim.max is not None
                else None,
            ),
            y_dim=Dimension(
                min=self.unit.convert(to_unit, self.y_dim.min)
                if self.y_dim.min is not None
                else None,
                max=self.unit.convert(to_unit, self.y_dim.max)
                if self.y_dim.max is not None
                else None,
            ),
            standardized=self.standardized,
            unit=to_unit,
            goal_width=self.unit.convert(to_unit, self.goal_width),
            goal_height=self.unit.convert(to_unit, self.goal_height)
            if self.goal_height is not None
            else None,
            six_yard_width=self.unit.convert(to_unit, self.six_yard_width),
            six_yard_length=self.unit.convert(to_unit, self.six_yard_length),
            penalty_area_width=self.unit.convert(
                to_unit, self.penalty_area_width
            ),
            penalty_area_length=self.unit.convert(
                to_unit, self.penalty_area_length
            ),
            circle_radius=self.unit.convert(to_unit, self.circle_radius),
            corner_radius=self.unit.convert(to_unit, self.corner_radius),
            penalty_spot_distance=self.unit.convert(
                to_unit, self.penalty_spot_distance
            ),
            penalty_arc_radius=self.unit.convert(
                to_unit, self.penalty_arc_radius
            ),
            pitch_length=self.pitch_length,
            pitch_width=self.pitch_width,
        )

    def _transformation_zones_x(self, length: float):
        assert self.x_dim.min is not None
        penalty_arc = self.penalty_spot_distance + self.penalty_arc_radius
        return [
            # goal line to 6 yard box
            (self.x_dim.min, self.x_dim.min + self.six_yard_length),
            # 6 yard box to penalty spot
            (
                self.x_dim.min + self.six_yard_length,
                self.x_dim.min + self.penalty_spot_distance,
            ),
            # penalty spot to penalty area
            (
                self.x_dim.min + self.penalty_spot_distance,
                self.x_dim.min + self.penalty_area_length,
            ),
            # penalty area to penalty arc
            (
                self.x_dim.min + self.penalty_area_length,
                self.x_dim.min + penalty_arc,
            ),
            # penalty arc to center circle
            (
                self.x_dim.min + penalty_arc,
                self.x_dim.min + length / 2 - self.circle_radius,
            ),
            # center circle to center line
            (
                self.x_dim.min + length / 2 - self.circle_radius,
                self.x_dim.min + length / 2,
            ),
        ]

    def _transformation_zones_y(self, width: float):
        assert self.y_dim.min is not None
        return [
            # side line to penalty area
            (
                self.y_dim.min,
                self.y_dim.min + (width - self.penalty_area_width) / 2,
            ),
            # penalty area to six yard box
            (
                self.y_dim.min + (width - self.penalty_area_width) / 2,
                self.y_dim.min + (width - self.six_yard_width) / 2,
            ),
            # six yard box to inside goalpost
            (
                self.y_dim.min + (width - self.six_yard_width) / 2,
                self.y_dim.min + (width - self.goal_width) / 2,
            ),
            # inside goalpost to center
            (
                self.y_dim.min + (width - self.goal_width) / 2,
                self.y_dim.min + width / 2,
            ),
        ]

    def to_metric_base(
        self,
        point: Point,
        pitch_length: float = DEFAULT_PITCH_LENGTH,
        pitch_width: float = DEFAULT_PITCH_WIDTH,
    ) -> Point:
        """
        Convert a point from this pitch dimensions to the IFAB pitch dimensions.

        Arguments:
            point: The point to convert

        Returns:
            The point in the IFAB pitch dimensions
        """
        if (
            self.x_dim.min is None
            or self.x_dim.max is None
            or self.y_dim.min is None
            or self.y_dim.max is None
        ):
            raise MissingDimensionError(
                "The pitch boundaries need to be fully specified to convert coordinates."
            )

        ifab_dims = MetricPitchDimensions(
            x_dim=Dimension(0, pitch_length),
            y_dim=Dimension(0, pitch_width),
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            standardized=False,
        )
        x_ifab_zones = ifab_dims._transformation_zones_x(pitch_length)
        y_ifab_zones = ifab_dims._transformation_zones_y(pitch_width)
        x_from_zones = self._transformation_zones_x(
            self.x_dim.max - self.x_dim.min
        )
        y_from_zones = self._transformation_zones_y(
            self.y_dim.max - self.y_dim.min
        )

        def transform(v, from_zones, from_length, ifab_zones, ifab_length):
            mirror = False
            if v > from_zones[-1][1]:
                v = from_length - (v - from_zones[0][0]) + from_zones[0][0]
                mirror = True
            # find the zone the v coordinate is in
            try:
                zone = next(
                    (
                        idx
                        for idx, zone in enumerate(from_zones)
                        if zone[0] <= v <= zone[1]
                    )
                )
                scale = (
                    # length of the zone in IFAB dimensions
                    (ifab_zones[zone][1] - ifab_zones[zone][0])
                    # length of the zone in the original dimensions
                    / (from_zones[zone][1] - from_zones[zone][0])
                )
                # ifab = smallest IFAB value of the zone + (v - smallest v value of the zone) * scaling factor of the zone
                ifab = ifab_zones[zone][0] + (v - from_zones[zone][0]) * scale
            except StopIteration:
                # value is outside of the pitch dimensions
                ifab = ifab_zones[0][0] + (v - from_zones[0][0]) * (
                    ifab_length / from_length
                )
            if mirror:
                ifab = ifab_length - ifab
            return ifab

        if isinstance(point, Point3D):
            return Point3D(
                x=transform(
                    point.x,
                    x_from_zones,
                    self.x_dim.max - self.x_dim.min,
                    x_ifab_zones,
                    pitch_length,
                ),
                y=transform(
                    point.y,
                    y_from_zones,
                    self.y_dim.max - self.y_dim.min,
                    y_ifab_zones,
                    pitch_width,
                ),
                z=(
                    point.z * 2.44 / self.goal_height
                    if self.goal_height is not None
                    else point.z
                )
                if point.z is not None
                else None,
            )
        else:
            return Point(
                x=transform(
                    point.x,
                    x_from_zones,
                    self.x_dim.max - self.x_dim.min,
                    x_ifab_zones,
                    pitch_length,
                ),
                y=transform(
                    point.y,
                    y_from_zones,
                    self.y_dim.max - self.y_dim.min,
                    y_ifab_zones,
                    pitch_width,
                ),
            )

    def from_metric_base(
        self,
        point: Point,
        pitch_length: float = DEFAULT_PITCH_LENGTH,
        pitch_width: float = DEFAULT_PITCH_WIDTH,
    ) -> Point:
        """
        Convert a point from the IFAB pitch dimensions to this pitch dimensions.

        Arguments:
            point: The point to convert

        Returns:
            The point in the regular pitch dimensions
        """
        if (
            self.x_dim.min is None
            or self.x_dim.max is None
            or self.y_dim.min is None
            or self.y_dim.max is None
        ):
            raise MissingDimensionError(
                "The pitch boundaries need to be fully specified to convert coordinates."
            )

        ifab_dims = MetricPitchDimensions(
            x_dim=Dimension(0, pitch_length),
            y_dim=Dimension(0, pitch_width),
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            standardized=False,
        )
        x_ifab_zones = ifab_dims._transformation_zones_x(pitch_length)
        y_ifab_zones = ifab_dims._transformation_zones_y(pitch_width)
        x_to_zones = self._transformation_zones_x(
            self.x_dim.max - self.x_dim.min
        )
        y_to_zones = self._transformation_zones_y(
            self.y_dim.max - self.y_dim.min
        )

        def transform(v, to_zones, to_length, ifab_zones, ifab_length):
            mirror = False
            if v > ifab_length / 2:
                v = ifab_length - v
                mirror = True
            # find the zone the v coordinate is in
            try:
                zone = next(
                    (
                        idx
                        for idx, zone in enumerate(ifab_zones)
                        if zone[0] <= v <= zone[1]
                    )
                )
                scale = (
                    # length of the zone in the original dimensions
                    (to_zones[zone][1] - to_zones[zone][0])
                    # length of the zone in IFAB dimensions
                    / (ifab_zones[zone][1] - ifab_zones[zone][0])
                )
                # ifab = smallest IFAB value of the zone + (v - smallest v value of the zone) * scaling factor of the zone
                v = to_zones[zone][0] + (v - ifab_zones[zone][0]) * scale
            except StopIteration:
                # value is outside of the pitch dimensions
                v = to_zones[0][0] + (v - ifab_zones[0][0]) * (
                    to_length / ifab_length
                )
            if mirror:
                v = (to_length + to_zones[0][0] - v) + to_zones[0][0]
            return v

        if isinstance(point, Point3D):
            return Point3D(
                x=transform(
                    point.x,
                    x_to_zones,
                    self.x_dim.max - self.x_dim.min,
                    x_ifab_zones,
                    pitch_length,
                ),
                y=transform(
                    point.y,
                    y_to_zones,
                    self.y_dim.max - self.y_dim.min,
                    y_ifab_zones,
                    pitch_width,
                ),
                z=(
                    point.z * self.goal_height / 2.44
                    if self.goal_height is not None
                    else point.z
                )
                if point.z is not None
                else None,
            )
        else:
            return Point(
                x=transform(
                    point.x,
                    x_to_zones,
                    self.x_dim.max - self.x_dim.min,
                    x_ifab_zones,
                    pitch_length,
                ),
                y=transform(
                    point.y,
                    y_to_zones,
                    self.y_dim.max - self.y_dim.min,
                    y_ifab_zones,
                    pitch_width,
                ),
            )

    def distance_between(
        self, point1: Point, point2: Point, unit: Unit = Unit.METERS
    ) -> float:
        """
        Calculate the distance between two points in the coordinate system.

        Arguments:
            point1: The first point
            point2: The second point
            unit: The unit to measure the distance in

        Returns:
            The distance between the two points in the given unit
        """
        if self.pitch_length is None or self.pitch_width is None:
            warnings.warn(
                "The pitch length and width are not specified. "
                "Assuming a standard pitch size of 105x68 meters. "
                "This may lead to incorrect results.",
                stacklevel=2,
            )
            pitch_length = DEFAULT_PITCH_LENGTH
            pitch_width = DEFAULT_PITCH_WIDTH
        else:
            pitch_length = self.pitch_length
            pitch_width = self.pitch_width
        point1_ifab = self.to_metric_base(point1, pitch_length, pitch_width)
        point2_ifab = self.to_metric_base(point2, pitch_length, pitch_width)
        dist = point1_ifab.distance_to(point2_ifab)
        return Unit.METERS.convert(unit, dist)


@dataclass
class MetricPitchDimensions(PitchDimensions):
    """The standard pitch dimensions in meters by IFAB regulations.

    For national matches, the length of the pitch can be between 90 and 120
    meters, and the width can be between 45 and 90 meters. For international
    matches, the length can be between 100 and 110 meters, and the width can
    be between 64 and 75 meters. All other dimensions are fixed.

    See https://www.theifab.com/laws/latest/the-field-of-play.
    """

    unit: Unit = Unit.METERS

    goal_width: float = 7.32
    goal_height: Optional[float] = 2.44
    six_yard_width: float = 18.32
    six_yard_length: float = 5.5
    penalty_area_width: float = 40.32
    penalty_area_length: float = 16.5
    circle_radius: float = 9.15
    corner_radius: float = 1
    penalty_spot_distance: float = 11
    penalty_arc_radius: float = 9.15


@dataclass
class ImperialPitchDimensions(PitchDimensions):
    """The standard pitch dimensions in yards by IFAB regulations.

    For national matches, the length of the pitch can be between 100 and 130
    yards, and the width can be between 50 and 100 yards. For international
    matches, the length can be between 110 and 120 yards, and the width can
    be between 70 and 80 yards. All other dimensions are fixed.

    See https://www.theifab.com/laws/latest/the-field-of-play.
    """

    unit: Unit = Unit.YARDS

    goal_width: float = 8
    goal_height: Optional[float] = 2.66
    six_yard_width: float = 20
    six_yard_length: float = 6
    penalty_area_width: float = 44
    penalty_area_length: float = 18
    circle_radius: float = 10
    corner_radius: float = 1
    penalty_spot_distance: float = 12
    penalty_arc_radius: float = 10


@dataclass
class NormalizedPitchDimensions(MetricPitchDimensions):
    """The standard pitch dimensions in normalized units.

    The pitch dimensions are normalized to a unit square, where the length
    and width of the pitch are 1. All other dimensions are scaled accordingly.
    """

    x_dim: Dimension = Dimension(0, 1)
    y_dim: Dimension = Dimension(0, 1)
    standardized: bool = False
    unit: Unit = Unit.NORMED

    def __post_init__(self):
        if self.pitch_length is None or self.pitch_width is None:
            raise ValueError("The pitch length and width need to be specified")
        dim_width = self.y_dim.max - self.y_dim.min
        dim_length = self.x_dim.max - self.x_dim.min
        self.goal_width = self.goal_width / self.pitch_width * dim_width
        self.six_yard_width = (
            self.six_yard_width / self.pitch_width * dim_width
        )
        self.six_yard_length = (
            self.six_yard_length / self.pitch_length * dim_length
        )
        self.penalty_area_width = (
            self.penalty_area_width / self.pitch_width * dim_width
        )
        self.penalty_area_length = (
            self.penalty_area_length / self.pitch_length * dim_length
        )
        self.circle_radius = (
            self.circle_radius / self.pitch_length * dim_length
        )
        self.corner_radius = (
            self.corner_radius / self.pitch_length * dim_length
        )
        self.penalty_spot_distance = (
            self.penalty_spot_distance / self.pitch_length * dim_length
        )
        self.penalty_arc_radius = (
            self.penalty_arc_radius / self.pitch_length * dim_length
        )


@dataclass
class OptaPitchDimensions(PitchDimensions):
    """The pitch dimensions used by Opta."""

    x_dim: Dimension = Dimension(0, 100)
    y_dim: Dimension = Dimension(0, 100)
    standardized: bool = True
    unit: Unit = Unit.NORMED

    goal_width: float = 9.6
    goal_height: Optional[float] = 38
    six_yard_width: float = 26.4
    six_yard_length: float = 5.8
    penalty_area_width: float = 57.8
    penalty_area_length: float = 17.0
    circle_radius: float = 9.00
    corner_radius: float = 0.97
    penalty_spot_distance: float = 11.5
    penalty_arc_radius: float = 8.9


@dataclass
class WyscoutPitchDimensions(PitchDimensions):
    """The pitch dimensions used by Wyscout."""

    x_dim: Dimension = Dimension(0, 100)
    y_dim: Dimension = Dimension(0, 100)
    standardized: bool = True
    unit: Unit = Unit.NORMED

    goal_width: float = 12.0
    goal_height: Optional[float] = None
    six_yard_width: float = 26.0
    six_yard_length: float = 6.0
    penalty_area_width: float = 62.0
    penalty_area_length: float = 16.0
    circle_radius: float = 8.84  # inferred
    corner_radius: float = 0.97  # inferred
    penalty_spot_distance: float = 10.0
    penalty_arc_radius: float = 7.74  # inferred
