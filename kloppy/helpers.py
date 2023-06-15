from typing import Union, Optional
from collections.abc import Sequence

from .domain import (
    Dataset,
    Dimension,
    Orientation,
    PitchDimensions,
    DatasetTransformer,
    Provider,
    build_coordinate_system,
    CoordinateSystem,
)


def transform(
    dataset: Dataset,
    to_orientation: Optional[Union[Orientation, str]] = None,
    to_pitch_dimensions: Optional[Union[PitchDimensions, Sequence]] = None,
    to_coordinate_system: Optional[
        Union[CoordinateSystem, Provider, str]
    ] = None,
) -> Dataset:
    # convert raw orientation to object
    if to_orientation is not None and isinstance(to_orientation, str):
        to_orientation = Orientation[to_orientation.upper()]

    # convert raw pitch dimensions to object
    if to_pitch_dimensions is not None and isinstance(
        to_pitch_dimensions, Sequence
    ):
        to_pitch_dimensions = PitchDimensions(
            x_dim=Dimension(*to_pitch_dimensions[0]),
            y_dim=Dimension(*to_pitch_dimensions[1]),
        )

    # convert raw coordinate system to object
    if to_coordinate_system is not None:
        if isinstance(to_coordinate_system, str):
            to_coordinate_system = build_coordinate_system(
                provider=Provider[to_coordinate_system.upper()],
                length=dataset.metadata.coordinate_system.length,
                width=dataset.metadata.coordinate_system.width,
            )
        elif isinstance(to_coordinate_system, Provider):
            to_coordinate_system = build_coordinate_system(
                provider=to_coordinate_system,
                length=dataset.metadata.coordinate_system.length,
                width=dataset.metadata.coordinate_system.width,
            )

    return DatasetTransformer.transform_dataset(
        dataset=dataset,
        to_orientation=to_orientation,
        to_coordinate_system=to_coordinate_system,
        to_pitch_dimensions=to_pitch_dimensions,
    )
