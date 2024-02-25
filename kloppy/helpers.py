from typing import Union, Optional

from .domain import (
    Dataset,
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
    to_pitch_dimensions: Optional[PitchDimensions] = None,
    to_coordinate_system: Optional[
        Union[CoordinateSystem, Provider, str]
    ] = None,
) -> Dataset:
    # convert raw orientation to object
    if to_orientation is not None and isinstance(to_orientation, str):
        to_orientation = Orientation[to_orientation.upper()]

    # convert raw coordinate system to object
    if to_coordinate_system is not None:
        if isinstance(to_coordinate_system, str):
            to_coordinate_system = build_coordinate_system(
                provider=Provider[to_coordinate_system.upper()],
                pitch_length=dataset.metadata.coordinate_system.pitch_length,
                pitch_width=dataset.metadata.coordinate_system.pitch_width,
            )
        elif isinstance(to_coordinate_system, Provider):
            to_coordinate_system = build_coordinate_system(
                provider=to_coordinate_system,
                pitch_length=dataset.metadata.coordinate_system.pitch_length,
                pitch_width=dataset.metadata.coordinate_system.pitch_width,
            )

    return DatasetTransformer.transform_dataset(
        dataset=dataset,
        to_orientation=to_orientation,
        to_coordinate_system=to_coordinate_system,
        to_pitch_dimensions=to_pitch_dimensions,
    )
