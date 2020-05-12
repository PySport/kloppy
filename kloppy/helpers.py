from typing import Callable, TypeVar

from . import TRACABSerializer, MetricaTrackingSerializer
from .domain import DataSet, Frame, TrackingDataSet, Transformer, Orientation, PitchDimensions, Dimension


def load_tracab_tracking_data(meta_data_filename: str, raw_data_filename: str, options: dict = None) -> DataSet:
    serializer = TRACABSerializer()
    with open(meta_data_filename, "rb") as meta_data, \
            open(raw_data_filename, "rb") as raw_data:

        return serializer.deserialize(
            inputs={
                'meta_data': meta_data,
                'raw_data': raw_data
            },
            options=options
        )


def load_metrica_tracking_data(raw_data_home_filename: str, raw_data_away_filename: str, options: dict = None) -> DataSet:
    serializer = MetricaTrackingSerializer()
    with open(raw_data_home_filename, "rb") as raw_data_home, \
            open(raw_data_away_filename, "rb") as raw_data_away:

        return serializer.deserialize(
            inputs={
                'raw_data_home': raw_data_home,
                'raw_data_away': raw_data_away
            },
            options=options
        )


DataSetType = TypeVar('DataSetType')


def transform(data_set: DataSetType, to_orientation=None, to_pitch_dimensions=None) -> DataSetType:
    if to_orientation and isinstance(to_orientation, str):
        to_orientation = Orientation[to_orientation]
    if to_pitch_dimensions and (isinstance(to_pitch_dimensions, list) or isinstance(to_pitch_dimensions, tuple)):
        to_pitch_dimensions = PitchDimensions(
            x_dim=Dimension(*to_pitch_dimensions[0]),
            y_dim=Dimension(*to_pitch_dimensions[1])
        )
    return Transformer.transform_data_set(
        data_set=data_set,
        to_orientation=to_orientation,
        to_pitch_dimensions=to_pitch_dimensions
    )


def _frame_to_pandas_row_converter(frame: Frame) -> dict:
    row = dict(
        period_id=frame.period.id,
        timestamp=frame.timestamp,
        ball_state=frame.ball_state,
        ball_owning_team=frame.ball_owning_team,
        ball_x=frame.ball_position.x if frame.ball_position else None,
        ball_y=frame.ball_position.y if frame.ball_position else None
    )
    for jersey_no, position in frame.home_team_player_positions.items():
        row.update({
            f'player_home_{jersey_no}_x': position.x,
            f'player_home_{jersey_no}_y': position.y
        })
    for jersey_no, position in frame.away_team_player_positions.items():
        row.update({
            f'player_away_{jersey_no}_x': position.x,
            f'player_away_{jersey_no}_y': position.y
        })
    
    return row


def to_pandas(data_set: DataSet, _record_converter: Callable = None) -> 'DataFrame':
    try:
        import pandas as pd
    except ImportError:
        raise Exception("Seems like you don't have pandas installed. Please"
                        " install it using: pip install pandas")

    if not _record_converter:
        if isinstance(data_set, TrackingDataSet):
            _record_converter = _frame_to_pandas_row_converter
        else:
            raise Exception("Unknown dataset type")

    return pd.DataFrame.from_records(
        map(_record_converter, data_set.records)
    )
