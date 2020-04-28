from typing import Tuple, List, Dict, Iterator

import heapq

from ....domain import attacking_direction_from_frame
from ....domain.models import (
    DataSet,
    AttackingDirection,
    Frame,
    Point,
    Period,
    Orientation,
    PitchDimensions,
    Dimension, DataSetFlag)
from ...utils import Readable, performance_logging
from . import TrackingDataSerializer


# PartialFrame = namedtuple("PartialFrame", "team period frame_id player_positions ball_position")


def create_iterator(data: Readable, sample_rate: float) -> Iterator:
    """
    Sample file:

    ,,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,,Away,
    ,,,25,,15,,16,,17,,18,,19,,20,,21,,22,,23,,24,,26,,27,,28,,,
    Period,Frame,Time [s],Player25,,Player15,,Player16,,Player17,,Player18,,Player19,,Player20,,Player21,,Player22,,Player23,,Player24,,Player26,,Player27,,Player28,,Ball,
    1,1,0.04,0.90509,0.47462,0.58393,0.20794,0.67658,0.4671,0.6731,0.76476,0.40783,0.61525,0.45472,0.38709,0.5596,0.67775,0.55243,0.43269,0.50067,0.94322,0.43693,0.05002,0.37833,0.27383,NaN,NaN,NaN,NaN,NaN,NaN,0.45472,0.38709

    Notes:
        1. the y-axe is flipped because Metrica use (y, -y) instead of (-y, y)
    """
    # lines = list(map(lambda x: x.strip().decode("ascii"), data.readlines()))

    team = None
    frame_idx = 0
    frame_sample = 1 / sample_rate
    player_jersey_numbers = []
    period = None

    for i, line in enumerate(data):
        line = line.strip().decode('ascii')
        columns = line.split(',')
        if i == 0:
            # team
            pass
        elif i == 1:
            player_jersey_numbers = columns[3:-2:2]
        elif i == 2:
            # consider doing some validation on the columns
            pass
        else:

            period_id = int(columns[0])
            frame_id = int(columns[1])

            if period is None or period.id != period_id:
                period = Period(
                    id=period_id,
                    start_frame_id=frame_id,
                    end_frame_id=frame_id
                )
            else:
                # consider not update this every frame for performance reasons
                period.end_frame_id = frame_id

            if frame_idx % frame_sample == 0:
                yield dict(
                    # Period will be updated during reading the file....
                    # Might introduce bugs here
                    period=period,
                    frame_id=frame_id,
                    player_positions={
                        player_no: Point(
                            x=float(columns[3 + i * 2]),
                            y=-1 * float(columns[3 + i * 2 + 1])
                        )
                        for i, player_no in enumerate(player_jersey_numbers)
                        if columns[3 + i * 2] != 'NaN'
                    },
                    ball_position=Point(
                        x=float(columns[-2]),
                        y=-1 * float(columns[-1])
                    )
                )
            frame_idx += 1


class MetricaTrackingSerializer(TrackingDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "home_raw_data" not in inputs:
            raise ValueError("Please specify a value for 'home_raw_data'")
        if "away_raw_data" not in inputs:
            raise ValueError("Please specify a value for 'away_raw_data'")

    def deserialize(self, inputs: Dict[str, Readable], options: Dict = None) -> DataSet:
        self.__validate_inputs(inputs)
        if not options:
            options = {}

        sample_rate = float(options.get('sample_rate', 1.0))

        with performance_logging("prepare"):
            home_iterator = create_iterator(inputs['home_raw_data'], sample_rate)
            away_iterator = create_iterator(inputs['away_raw_data'], sample_rate)

            partial_frames = zip(home_iterator, away_iterator)

        with performance_logging("loading"):
            frames = []
            periods = []
            # consider reading this from data
            frame_rate = 25
            for home_partial_frame, away_partial_frame in partial_frames:
                assert home_partial_frame['frame_id'] == away_partial_frame['frame_id'], "Mismatch"

                period: Period = home_partial_frame['period']
                frame_id: int = home_partial_frame['frame_id']

                frame = Frame(
                    frame_id=home_partial_frame['frame_id'],
                    # -1 needed because frame_id is 1-based
                    timestamp=(frame_id - (period.start_frame_id - 1)) / frame_rate,
                    ball_position=home_partial_frame['ball_position'],
                    home_team_player_positions=home_partial_frame['player_positions'],
                    away_team_player_positions=away_partial_frame['player_positions'],
                    period=period,
                    ball_state=None,
                    ball_owning_team=None
                )

                frames.append(frame)

                if not periods or period.id != periods[-1].id:
                    periods.append(period)

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
            flags=~(DataSetFlag.BALL_STATE | DataSetFlag.BALL_OWNING_TEAM),
            frame_rate=frame_rate,
            orientation=orientation,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, 1),
                y_dim=Dimension(0, 1)
            ),
            periods=periods,
            frames=frames
        )

    def serialize(self, data_set: DataSet) -> Tuple[str, str]:
        raise NotImplementedError
