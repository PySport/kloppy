from kloppy.domain import (CustomCoordinateSystem,NormalizedPitchDimensions,Dimension,VerticalOrientation,Origin)

class CDFCoordinateSystem:


    def __init__(self, dataset):
        self.length = dataset.metadata.pitch_dimensions.pitch_length
        self.width = dataset.metadata.pitch_dimensions.pitch_width
        # build the cdf normalize coordinate system
        self.coordinate_system = CustomCoordinateSystem(
            origin=Origin.CENTER,
            vertical_orientation=VerticalOrientation.BOTTOM_TO_TOP,
            pitch_dimensions=NormalizedPitchDimensions(
                x_dim=Dimension(min=-self.length / 2, max=self.length / 2),
                y_dim=Dimension(min=-self.width / 2, max=self.width / 2),
                pitch_length= self.length,
                pitch_width= self.width,
            ),
        )

    def get_coordinate_system(self):
        """Return the built coordinate system."""
        return self.coordinate_system