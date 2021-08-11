from kloppy.domain import Dimension, PitchDimensions


class TestPitchdimensions:
    def test_pitchdimensions_properties(self):
        pitch_without_scale = PitchDimensions(
            x_dim=Dimension(-100, 100), y_dim=Dimension(-50, 50)
        )

        assert pitch_without_scale.length is None
        assert pitch_without_scale.width is None

        pitch_with_scale = PitchDimensions(
            x_dim=Dimension(-100, 100),
            y_dim=Dimension(-50, 50),
            length=120,
            width=80,
        )

        assert pitch_with_scale.length == 120
        assert pitch_with_scale.width == 80
