from math import sqrt
import pytest

from kloppy.domain import (
    Dimension,
    NormalizedPitchDimensions,
    Point,
    Point3D,
    OptaPitchDimensions,
    Unit,
    MetricPitchDimensions,
)
from kloppy.domain.services.transformers import DatasetTransformer


class TestPitchdimensions:
    def test_normalized_pitchdimensions(self):
        pitch_with_scale = NormalizedPitchDimensions(
            x_dim=Dimension(-100, 100),
            y_dim=Dimension(-50, 50),
            pitch_length=120,
            pitch_width=80,
        )

        assert pitch_with_scale.pitch_length == 120
        assert pitch_with_scale.pitch_width == 80

    def test_to_metric_base_dimensions(self):
        pitch = OptaPitchDimensions()

        ifab_point = pitch.to_metric_base(Point(11.5, 50))
        assert ifab_point == Point(11, 34)

        ifab_point = pitch.to_metric_base(Point3D(0, 50, 38))
        assert ifab_point == Point3D(0, 34, 2.44)

        ifab_point = pitch.to_metric_base(
            Point(60, 61), pitch_length=105, pitch_width=68
        )
        assert round(ifab_point.x, 2) == 62.78
        assert round(ifab_point.y, 2) == 41.72

    def test_to_metric_base_dimensions_out_of_bounds(self):
        pitch = NormalizedPitchDimensions(
            x_dim=Dimension(-100, 100),
            y_dim=Dimension(-50, 50),
            pitch_length=120,
            pitch_width=80,
        )
        ifab_point = pitch.to_metric_base(Point(-100, 0))
        assert ifab_point == Point(0, 34)
        ifab_point = pitch.to_metric_base(Point(-105, 0))
        assert ifab_point == Point(-2.625, 34)
        ifab_point = pitch.to_metric_base(Point(105, 0))
        assert ifab_point == Point(107.625, 34)

    def test_from_metric_base_dimensions(self):
        pitch = OptaPitchDimensions()

        opta_point = pitch.from_metric_base(Point(11, 34))
        assert opta_point == Point(11.5, 50)

        opta_point = pitch.from_metric_base(Point3D(0, 34, 2.44))
        assert opta_point == Point3D(0, 50, 38)

        ifab_point = pitch.from_metric_base(
            Point(62.78, 41.72), pitch_length=105, pitch_width=68
        )
        assert round(ifab_point.x, 2) == 60
        assert round(ifab_point.y, 2) == 61

    def test_from_metric_base_dimensions_out_of_bounds(self):
        pitch = NormalizedPitchDimensions(
            x_dim=Dimension(-100, 100),
            y_dim=Dimension(-50, 50),
            pitch_length=120,
            pitch_width=80,
        )
        point = pitch.from_metric_base(Point(0, 34))
        assert point == Point(-100, 0)
        point = pitch.from_metric_base(Point(-2.625, 34))
        assert point == Point(-105, 0)
        point = pitch.from_metric_base(Point(107.625, 34))
        assert point == Point(105, 0)

    def test_distance_between(self):
        pitch = OptaPitchDimensions(pitch_length=105, pitch_width=68)

        distance = pitch.distance_between(
            Point(0, 0),
            Point(100, 100),
        )
        assert distance == sqrt(105**2 + 68**2)

        distance = pitch.distance_between(Point(0, 50), Point(11.5, 50))
        assert distance == 11

        distance = pitch.distance_between(
            Point(100, 50), Point(100 - 11.5, 50)
        )
        assert distance == 11

        distance = pitch.distance_between(
            Point(0, 50), Point(11.5, 50), unit=Unit.CENTIMETERS
        )
        assert distance == 1100

        pitch = NormalizedPitchDimensions(
            x_dim=Dimension(-100, 100),
            y_dim=Dimension(-50, 50),
            pitch_length=120,
            pitch_width=80,
        )
        distance = pitch.distance_between(
            Point(-100, -50),
            Point(100, 50),
        )
        assert distance == sqrt(120**2 + 80**2)

    def test_transform(self):
        transformer = DatasetTransformer(
            from_pitch_dimensions=OptaPitchDimensions(),
            to_pitch_dimensions=MetricPitchDimensions(
                x_dim=Dimension(0, 105),
                y_dim=Dimension(0, 68),
                pitch_length=105,
                pitch_width=68,
                standardized=False,
            ),
        )
        # the corner of the penalty area should remain the corner of
        # the penalty area in the new coordinate system
        transformed_point = transformer.change_point_dimensions(
            Point(17, 78.9)
        )
        assert transformed_point.x == pytest.approx(16.5)
        assert transformed_point.y == pytest.approx(54.16)
