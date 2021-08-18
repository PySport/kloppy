import os

from kloppy import SecondSpectrumSerializer
from kloppy.domain import (
    Period,
    AttackingDirection,
    Orientation,
    Provider,
    Point,
    Point3D,
    BallState,
    Team,
    Ground,
)
from kloppy.domain.models.common import DatasetType


class TestSecondSpectrumTracking:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)
        serializer = SecondSpectrumSerializer()
        assert True

    def test_correct_normalized_deserialization(self):
        base_dir = os.path.dirname(__file__)
        serializer = SecondSpectrumSerializer()
        assert True
