from ...models import (
    Point,
    CoordinateSystem,
    Orientation,
    Frame,
    DataSet)


class VoidPointTransformer(object):
    def transform_point(self, point: Point) -> Point:
        return point


class Transformer(object):
    def __init__(self,
                 from_coordinate_system: CoordinateSystem, from_orientation: Orientation,
                 to_coordinate_system: CoordinateSystem, to_orientation: Orientation):
        self._from_coordinate_system = from_coordinate_system
        self._from_orientation = from_orientation
        self._to_coordinate_system = to_coordinate_system
        self._to_orientation = to_orientation

    def transform_point(self, point: Point, flip: bool) -> Point:
        # 1. always apply changes from coordinate system
        # 2. flip coordinates depending on orientation
        x_base = self._from_coordinate_system.x_scale.to_base(point.x)
        y_base = self._from_coordinate_system.y_scale.to_base(point.y)

        if flip:
            x_base = 1 - x_base
            y_base = 1 - y_base

        return Point(
            x=self._to_coordinate_system.x_scale.from_base(x_base),
            y=self._to_coordinate_system.y_scale.from_base(y_base)
        )

    def transform_frame(self, frame: Frame) -> Frame:
        flip = False
        return Frame(
            # doesn't change
            frame_id=frame.frame_id,
            ball_owning_team=frame.ball_owning_team,
            ball_state=frame.ball_state,
            period=frame.period,

            # changes
            ball_position=self.transform_point(frame.ball_position, flip),

            # bla
            home_team_player_positions={
                jersey_no: self.transform_point(point, flip)
                for jersey_no, point
                in frame.home_team_player_positions.items()
            },
            away_team_player_positions={
                jersey_no: self.transform_point(point, flip)
                for jersey_no, point
                in frame.away_team_player_positions.items()
            },
            game_statics=None
        )

    @classmethod
    def transform_data_set(cls,
                           data_set: DataSet,
                           to_coordinate_system: CoordinateSystem,
                           to_orientation: Orientation) -> DataSet:
        transformer = cls(
            from_coordinate_system=data_set.coordinate_system,
            from_orientation=data_set.orientation,
            to_coordinate_system=to_coordinate_system,
            to_orientation=to_orientation
        )
        frames = list(map(transformer.transform_frame, data_set.frames))

        return DataSet(
            frame_rate=data_set.frame_rate,
            periods=data_set.periods,
            coordinate_system=to_coordinate_system,
            orientation=to_orientation,
            frames=frames
        )
