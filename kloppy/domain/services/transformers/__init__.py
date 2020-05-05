from kloppy.domain import (
    Point,
    PitchDimensions,
    Orientation,
    Frame,
    Team, AttackingDirection,

    TrackingDataSet, DataSetFlag, DataSet, # NOT YET: EventDataSet
)


class Transformer:
    def __init__(self,
                 from_pitch_dimensions: PitchDimensions, from_orientation: Orientation,
                 to_pitch_dimensions: PitchDimensions, to_orientation: Orientation):
        self._from_pitch_dimensions = from_pitch_dimensions
        self._from_orientation = from_orientation
        self._to_pitch_dimensions = to_pitch_dimensions
        self._to_orientation = to_orientation

    def transform_point(self, point: Point, flip: bool) -> Point:
        # 1. always apply changes from coordinate system
        # 2. flip coordinates depending on orientation
        x_base = self._from_pitch_dimensions.x_dim.to_base(point.x)
        y_base = self._from_pitch_dimensions.y_dim.to_base(point.y)

        if flip:
            x_base = 1 - x_base
            y_base = 1 - y_base

        return Point(
            x=self._to_pitch_dimensions.x_dim.from_base(x_base),
            y=self._to_pitch_dimensions.y_dim.from_base(y_base)
        )
    
    def __needs_flip(self, ball_owning_team: Team, attacking_direction: AttackingDirection) -> bool:
        if self._from_orientation == self._to_orientation:
            flip = False
        else:
            orientation_factor_from = self._from_orientation.get_orientation_factor(
                ball_owning_team=ball_owning_team,
                attacking_direction=attacking_direction
            )
            orientation_factor_to = self._to_orientation.get_orientation_factor(
                ball_owning_team=ball_owning_team,
                attacking_direction=attacking_direction
            )
            flip = orientation_factor_from != orientation_factor_to
        return flip

    def transform_frame(self, frame: Frame) -> Frame:
        flip = self.__needs_flip(
            ball_owning_team=frame.ball_owning_team,
            attacking_direction=frame.period.attacking_direction
        )

        return Frame(
            # doesn't change
            timestamp=frame.timestamp,
            frame_id=frame.frame_id,
            ball_owning_team=frame.ball_owning_team,
            ball_state=frame.ball_state,
            period=frame.period,

            # changes
            ball_position=self.transform_point(frame.ball_position, flip),
            home_team_player_positions={
                jersey_no: self.transform_point(point, flip)
                for jersey_no, point
                in frame.home_team_player_positions.items()
            },
            away_team_player_positions={
                jersey_no: self.transform_point(point, flip)
                for jersey_no, point
                in frame.away_team_player_positions.items()
            }
        )

    @classmethod
    def transform_data_set(cls,
                           data_set: DataSet,
                           to_pitch_dimensions: PitchDimensions = None,
                           to_orientation: Orientation = None) -> DataSet:
        if not to_pitch_dimensions and not to_orientation:
            return data_set
        elif not to_orientation:
            to_orientation = data_set.orientation
        elif not to_pitch_dimensions:
            to_pitch_dimensions = data_set.pitch_dimensions

        if to_orientation == Orientation.BALL_OWNING_TEAM:
            if not data_set.flags & DataSetFlag.BALL_OWNING_TEAM:
                raise ValueError("Cannot transform to BALL_OWNING_TEAM orientation when dataset doesn't contain "
                                 "ball owning team data")

        transformer = cls(
            from_pitch_dimensions=data_set.pitch_dimensions,
            from_orientation=data_set.orientation,
            to_pitch_dimensions=to_pitch_dimensions,
            to_orientation=to_orientation
        )
        if isinstance(data_set, TrackingDataSet):
            frames = list(map(transformer.transform_frame, data_set.records))

            return TrackingDataSet(
                flags=data_set.flags,
                frame_rate=data_set.frame_rate,
                periods=data_set.periods,
                pitch_dimensions=to_pitch_dimensions,
                orientation=to_orientation,
                records=frames
            )
        #elif isinstance(data_set, EventDataSet):
        #    raise Exception("EventDataSet transformer not implemented yet")
        else:
            raise Exception("Unknown DataSet type")
