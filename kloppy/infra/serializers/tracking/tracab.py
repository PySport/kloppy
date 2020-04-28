from typing import Tuple, Dict

from lxml import objectify

from kloppy.domain import (
    DataSet,
    AttackingDirection,
    Frame,
    Point,
    BallOwningTeam,
    BallState,
    Period,
    Orientation,
    PitchDimensions,
    Dimension,
    attacking_direction_from_frame,
    DataSetFlag)
from kloppy.infra.utils import Readable, performance_logging

from . import TrackingDataSerializer


class TRACABSerializer(TrackingDataSerializer):
    @classmethod
    def _frame_from_line(cls, period, line, frame_rate):
        line = str(line)
        frame_id, players, ball = line.strip().split(":")[:3]

        home_team_player_positions = {}
        away_team_player_positions = {}

        for player in players.split(";")[:-1]:
            team_id, target_id, jersey_no, x, y, speed = player.split(",")
            team_id = int(team_id)

            if team_id == 1:
                home_team_player_positions[jersey_no] = Point(float(x), float(y))
            elif team_id == 0:
                away_team_player_positions[jersey_no] = Point(float(x), float(y))

        ball_x, ball_y, ball_z, ball_speed, ball_owning_team, ball_state = ball.rstrip(";").split(",")[:6]

        frame_id = int(frame_id)

        return Frame(
            frame_id=frame_id,
            timestamp=(frame_id - period.start_frame_id) / frame_rate,
            ball_position=Point(float(ball_x), float(ball_y)),
            ball_state=BallState.from_string(ball_state),
            ball_owning_team=BallOwningTeam.from_string(ball_owning_team),
            home_team_player_positions=home_team_player_positions,
            away_team_player_positions=away_team_player_positions,
            period=period
        )

    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "meta_data" not in inputs:
            raise ValueError("Please specify a value for 'meta_data'")
        if "raw_data" not in inputs:
            raise ValueError("Please specify a value for 'raw_data'")

    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> DataSet:
        """
        Deserialize TRACAB tracking data into a `DataSet`.

        Parameters
        ----------
        inputs : dict
            input `raw_data` should point to a `Readable` object containing
            the 'csv' formatted raw data. input `meta_data` should point to
            the xml metadata data.
        options : dict
            Options for deserialization of the TRACAB file. Possible options are
            `only_alive` (boolean) to specify that only frames with alive ball state
            should be loaded, or `sample_rate` (float between 0 and 1) to specify
            the amount of frames that should be loaded.
        Returns
        -------
        data_set : DataSet
        Raises
        ------
        -

        See Also
        --------

        Examples
        --------
        >>> serializer = TRACABSerializer()
        >>> with open("metadata.xml", "rb") as meta, \
        >>>      open("raw.dat", "rb") as raw:
        >>>     data_set = serializer.deserialize(
        >>>         inputs={
        >>>             'meta_data': meta,
        >>>             'raw_data': raw
        >>>         },
        >>>         options={
        >>>             'only_alive': True,
        >>>             'sample_rate': 1/12
        >>>         }
        >>>     )
        """
        self.__validate_inputs(inputs)

        if not options:
            options = {}

        sample_rate = float(options.get('sample_rate', 1.0))
        only_alive = bool(options.get('only_alive', True))

        with performance_logging("Loading metadata"):
            match = objectify.fromstring(inputs['meta_data'].read()).match
            frame_rate = int(match.attrib['iFrameRateFps'])
            pitch_size_width = float(match.attrib['fPitchXSizeMeters'])
            pitch_size_height = float(match.attrib['fPitchYSizeMeters'])

            periods = []
            for period in match.iterchildren(tag='period'):
                start_frame_id = int(period.attrib['iStartFrame'])
                end_frame_id = int(period.attrib['iEndFrame'])
                if start_frame_id != 0 or end_frame_id != 0:
                    periods.append(
                        Period(
                            id=int(period.attrib['iId']),
                            start_frame_id=start_frame_id,
                            end_frame_id=end_frame_id
                        )
                    )

        with performance_logging("Loading data"):
            def _iter():
                n = 0
                sample = 1. / sample_rate

                for line in inputs['data'].readlines():
                    line = line.strip().decode("ascii")

                    frame_id = int(line[:10].split(":", 1)[0])
                    if only_alive and not line.endswith("Alive;:"):
                        continue

                    for period in periods:
                        if period.contains(frame_id):
                            if n % sample == 0:
                                yield period, line
                            n += 1

            frames = []
            for period, line in _iter():
                frame = self._frame_from_line(
                    period,
                    line,
                    frame_rate
                )

                if not period.attacking_direction_set:
                    period.set_attacking_direction(
                        attacking_direction=attacking_direction_from_frame(frame)
                    )

        orientation = (
            Orientation.FIXED_HOME_AWAY
            if periods[0].attacking_direction == AttackingDirection.HOME_AWAY else
            Orientation.FIXED_AWAY_HOME
        )

        return DataSet(
            flags=DataSetFlag.BALL_OWNING_TEAM | DataSetFlag.BALL_STATE,
            frame_rate=frame_rate,
            orientation=orientation,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(-1 * pitch_size_width / 2, pitch_size_width / 2),
                y_dim=Dimension(-1 * pitch_size_height / 2, pitch_size_height / 2),
                x_per_meter=100,
                y_per_meter=100
            ),
            periods=periods,
            frames=frames
        )

    def serialize(self, data_set: DataSet) -> Tuple[str, str]:
        raise NotImplementedError

