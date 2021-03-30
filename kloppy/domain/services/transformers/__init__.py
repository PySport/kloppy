from dataclasses import asdict, fields, replace
from typing import TypeVar

from kloppy.domain import (
    AttackingDirection,
    Dataset,
    DatasetFlag,
    EventDataset,
    Frame,
    Metadata,
    Orientation,
    PitchDimensions,
    Point,
    Team,
    TrackingDataset,
    CoordinateSystem,
    Origin,
)
from kloppy.domain.models.event import Event


class Transformer:
    def __init__(
        self,
        from_coordinate_system: CoordinateSystem = None,
        from_pitch_dimensions: PitchDimensions = None,
        from_orientation: Orientation = None,
        to_coordinate_system: CoordinateSystem = None,
        to_pitch_dimensions: PitchDimensions = None,
        to_orientation: Orientation = None,
    ):
        self._from_coordinate_system = from_coordinate_system
        self._from_pitch_dimensions = from_pitch_dimensions
        self._from_orientation = from_orientation
        self._to_coordinate_system = to_coordinate_system
        self._to_pitch_dimensions = to_pitch_dimensions
        self._to_orientation = to_orientation

    def change_point_dimensions(self, point: Point) -> Point:

        if point is None:
            return None

        x_base = self._from_pitch_dimensions.x_dim.to_base(point.x)
        y_base = self._from_pitch_dimensions.y_dim.to_base(point.y)

        return Point(
            x=self._to_pitch_dimensions.x_dim.from_base(x_base),
            y=self._to_pitch_dimensions.y_dim.from_base(y_base),
        )

    def flip_point(self, point: Point):

        if point is None:
            return None

        x_base = self._to_pitch_dimensions.x_dim.to_base(point.x)
        y_base = self._to_pitch_dimensions.y_dim.to_base(point.y)

        x_base = 1 - x_base
        y_base = 1 - y_base

        return Point(
            x=self._to_pitch_dimensions.x_dim.from_base(x_base),
            y=self._to_pitch_dimensions.y_dim.from_base(y_base),
        )

    def __needs_flip(
        self,
        ball_owning_team: Team,
        attacking_direction: AttackingDirection,
        action_executing_team: Team = None,
    ) -> bool:
        if self._from_orientation == self._to_orientation:
            flip = False
        else:
            orientation_factor_from = (
                self._from_orientation.get_orientation_factor(
                    ball_owning_team=ball_owning_team,
                    attacking_direction=attacking_direction,
                    action_executing_team=action_executing_team,
                )
            )
            orientation_factor_to = (
                self._to_orientation.get_orientation_factor(
                    ball_owning_team=ball_owning_team,
                    attacking_direction=attacking_direction,
                    action_executing_team=action_executing_team,
                )
            )
            flip = orientation_factor_from != orientation_factor_to
        return flip

    def transform_frame(self, frame: Frame) -> Frame:

        # Change coordinate system
        if self._to_coordinate_system is not None:
            frame = self.__change_frame_coordinate_system(frame)

        # Change dimensions
        if self._to_pitch_dimensions is not None:
            frame = self.__change_frame_dimensions(frame)

        # Flip frame based on orientation
        if self.__needs_flip(
            ball_owning_team=frame.ball_owning_team,
            attacking_direction=frame.period.attacking_direction,
        ):
            frame = self.__flip_frame(frame)

        return frame

    def __change_frame_coordinate_system(self, frame: Frame):

        return Frame(
            # doesn't change
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            ball_owning_team=frame.ball_owning_team,
            ball_state=frame.ball_state,
            period=frame.period,
            # changes
            ball_coordinates=self.__change_point_coordinate_system(
                frame.ball_coordinates
            ),
            players_coordinates={
                key: self.__change_point_coordinate_system(point)
                for key, point in frame.players_coordinates.items()
            },
        )

    def __change_frame_dimensions(self, frame: Frame):

        return Frame(
            # doesn't change
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            ball_owning_team=frame.ball_owning_team,
            ball_state=frame.ball_state,
            period=frame.period,
            # changes
            ball_coordinates=self.change_point_dimensions(
                frame.ball_coordinates
            ),
            players_coordinates={
                key: self.change_point_dimensions(point)
                for key, point in frame.players_coordinates.items()
            },
        )

    def __change_point_coordinate_system(self, point: Point):

        x = self._from_coordinate_system.pitch_dimensions.x_dim.to_base(
            point.x
        )
        y = self._from_coordinate_system.pitch_dimensions.y_dim.to_base(
            point.y
        )

        if (
            self._from_coordinate_system.vertical_orientation
            != self._to_coordinate_system.vertical_orientation
        ):
            y = 1 - y

        if not self._to_coordinate_system.normalized:
            x = self._to_coordinate_system.pitch_dimensions.x_dim.from_base(x)
            y = self._to_coordinate_system.pitch_dimensions.y_dim.from_base(y)

        return Point(x=x, y=y)

    def __flip_frame(self, frame: Frame):

        return Frame(
            # doesn't change
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            ball_owning_team=frame.ball_owning_team,
            ball_state=frame.ball_state,
            period=frame.period,
            # changes
            ball_coordinates=self.flip_point(frame.ball_coordinates),
            players_coordinates={
                key: self.flip_point(point)
                for key, point in frame.players_coordinates.items()
            },
        )

    def transform_event(self, event: Event) -> Event:
        flip = self.__needs_flip(
            ball_owning_team=event.ball_owning_team,
            attacking_direction=event.period.attacking_direction,
            action_executing_team=event.team,
        )

        position_changes = {
            field.name: self.transform_point(getattr(event, field.name), flip)
            for field in fields(event)
            if field.name.endswith("coordinates")
            and getattr(event, field.name)
        }

        return replace(event, **position_changes)

    @classmethod
    def transform_dataset(
        cls,
        dataset: Dataset,
        to_pitch_dimensions: PitchDimensions = None,
        to_orientation: Orientation = None,
    ) -> Dataset:
        if not to_pitch_dimensions and not to_orientation:
            return dataset
        elif not to_orientation:
            to_orientation = dataset.metadata.orientation
        elif not to_pitch_dimensions:
            to_pitch_dimensions = dataset.metadata.pitch_dimensions

        if to_orientation == Orientation.BALL_OWNING_TEAM:
            if not dataset.metadata.flags & DatasetFlag.BALL_OWNING_TEAM:
                raise ValueError(
                    "Cannot transform to BALL_OWNING_TEAM orientation when dataset doesn't contain "
                    "ball owning team data"
                )

        transformer = cls(
            from_pitch_dimensions=dataset.metadata.pitch_dimensions,
            from_orientation=dataset.metadata.orientation,
            to_pitch_dimensions=to_pitch_dimensions,
            to_orientation=to_orientation,
        )
        metadata = replace(
            dataset.metadata,
            pitch_dimensions=to_pitch_dimensions,
            orientation=to_orientation,
        )
        if isinstance(dataset, TrackingDataset):
            frames = [
                transformer.transform_frame(record)
                for record in dataset.records
            ]

            return TrackingDataset(
                metadata=metadata,
                records=frames,
            )
        elif isinstance(dataset, EventDataset):
            events = list(map(transformer.transform_event, dataset.records))

            return EventDataset(
                metadata=metadata,
                records=events,
            )
        else:
            raise Exception("Unknown Dataset type")
