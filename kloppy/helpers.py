from typing import Callable, TypeVar, Dict, Union

from . import (
    TRACABSerializer,
    MetricaTrackingSerializer,
    EPTSSerializer,
    StatsBombSerializer,
    OptaSerializer,
)
from .domain import (
    Dataset,
    Frame,
    Event,
    TrackingDataset,
    Transformer,
    Orientation,
    PitchDimensions,
    Dimension,
    EventDataset,
    PassEvent,
    CarryEvent,
    PassResult,
    EventType,
)


def load_tracab_tracking_data(
    meta_data_filename: str, raw_data_filename: str, options: dict = None
) -> TrackingDataset:
    serializer = TRACABSerializer()
    with open(meta_data_filename, "rb") as meta_data, open(
        raw_data_filename, "rb"
    ) as raw_data:

        return serializer.deserialize(
            inputs={"meta_data": meta_data, "raw_data": raw_data},
            options=options,
        )


def load_metrica_tracking_data(
    raw_data_home_filename: str,
    raw_data_away_filename: str,
    options: dict = None,
) -> TrackingDataset:
    serializer = MetricaTrackingSerializer()
    with open(raw_data_home_filename, "rb") as raw_data_home, open(
        raw_data_away_filename, "rb"
    ) as raw_data_away:

        return serializer.deserialize(
            inputs={
                "raw_data_home": raw_data_home,
                "raw_data_away": raw_data_away,
            },
            options=options,
        )


def load_epts_tracking_data(
    meta_data_filename: str, raw_data_filename: str, options: dict = None
) -> TrackingDataset:
    serializer = EPTSSerializer()
    with open(meta_data_filename, "rb") as meta_data, open(
        raw_data_filename, "rb"
    ) as raw_data:

        return serializer.deserialize(
            inputs={"meta_data": meta_data, "raw_data": raw_data},
            options=options,
        )


def load_statsbomb_event_data(
    event_data_filename: str, lineup_data_filename: str, options: dict = None
) -> EventDataset:
    serializer = StatsBombSerializer()
    with open(event_data_filename, "rb") as event_data, open(
        lineup_data_filename, "rb"
    ) as lineup_data:

        return serializer.deserialize(
            inputs={"event_data": event_data, "lineup_data": lineup_data},
            options=options,
        )


def load_opta_event_data(
    f24_data_filename: str, f7_data_filename: str, options: dict = None
) -> EventDataset:
    serializer = OptaSerializer()
    with open(f24_data_filename, "rb") as f24_data, open(
        f7_data_filename, "rb"
    ) as f7_data:

        return serializer.deserialize(
            inputs={"f24_data": f24_data, "f7_data": f7_data}, options=options,
        )


DatasetType = TypeVar("DatasetType")


def transform(
    dataset: DatasetType, to_orientation=None, to_pitch_dimensions=None
) -> DatasetType:
    if to_orientation and isinstance(to_orientation, str):
        to_orientation = Orientation[to_orientation]
    if to_pitch_dimensions and (
        isinstance(to_pitch_dimensions, list)
        or isinstance(to_pitch_dimensions, tuple)
    ):
        to_pitch_dimensions = PitchDimensions(
            x_dim=Dimension(*to_pitch_dimensions[0]),
            y_dim=Dimension(*to_pitch_dimensions[1]),
        )
    return Transformer.transform_dataset(
        dataset=dataset,
        to_orientation=to_orientation,
        to_pitch_dimensions=to_pitch_dimensions,
    )


def _frame_to_pandas_row_converter(frame: Frame) -> Dict:
    row = dict(
        period_id=frame.period.id if frame.period else None,
        timestamp=frame.timestamp,
        ball_state=frame.ball_state.value if frame.ball_state else None,
        ball_owning_team=frame.ball_owning_team.value
        if frame.ball_owning_team
        else None,
        ball_x=frame.ball_position.x if frame.ball_position else None,
        ball_y=frame.ball_position.y if frame.ball_position else None,
    )
    for jersey_no, position in frame.home_team_player_positions.items():
        row.update(
            {
                f"player_home_{jersey_no}_x": position.x,
                f"player_home_{jersey_no}_y": position.y,
            }
        )
    for jersey_no, position in frame.away_team_player_positions.items():
        row.update(
            {
                f"player_away_{jersey_no}_x": position.x,
                f"player_away_{jersey_no}_y": position.y,
            }
        )

    return row


def _event_to_pandas_row_converter(event: Event) -> Dict:
    row = dict(
        event_id=event.event_id,
        event_type=(
            event.event_type.value
            if event.event_type != EventType.GENERIC
            else f"GENERIC:{event.raw_event['type']['name']}"
        ),
        result=event.result.value if event.result else None,
        success=event.result.is_success if event.result else None,
        period_id=event.period.id,
        timestamp=event.timestamp,
        end_timestamp=None,
        ball_state=event.ball_state.value if event.ball_state else None,
        ball_owning_team=event.ball_owning_team.value
        if event.ball_owning_team
        else None,
        team=event.team.value,
        player_jersey_no=event.player_jersey_no,
        position_x=event.position.x if event.position else None,
        position_y=event.position.y if event.position else None,
    )
    if isinstance(event, PassEvent) and event.result == PassResult.COMPLETE:
        row.update(
            {
                "end_timestamp": event.receive_timestamp,
                "end_position_x": event.receiver_position.x,
                "end_position_y": event.receiver_position.y,
                "receiver_jersey_no": event.receiver_player_jersey_no,
            }
        )
    elif isinstance(event, CarryEvent):
        row.update(
            {
                "end_timestamp": event.end_timestamp,
                "end_position_x": event.end_position.x,
                "end_position_y": event.end_position.y,
            }
        )
    return row


def to_pandas(
    dataset: Dataset,
    _record_converter: Callable = None,
    additional_columns: Dict = None,
) -> "DataFrame":
    try:
        import pandas as pd
    except ImportError:
        raise Exception(
            "Seems like you don't have pandas installed. Please"
            " install it using: pip install pandas"
        )

    if not _record_converter:
        if isinstance(dataset, TrackingDataset):
            _record_converter = _frame_to_pandas_row_converter
        elif isinstance(dataset, EventDataset):
            _record_converter = _event_to_pandas_row_converter
        else:
            raise Exception("Unknown dataset type")

    def generic_record_converter(record: Union[Frame, Event]):
        row = _record_converter(record)
        if additional_columns:
            for k, v in additional_columns.items():
                if callable(v):
                    value = v(record)
                else:
                    value = v
                row.update({k: value})

        return row

    return pd.DataFrame.from_records(
        map(generic_record_converter, dataset.records)
    )


__all__ = [
    "load_tracab_tracking_data",
    "load_metrica_tracking_data",
    "load_epts_tracking_data",
    "load_statsbomb_event_data",
    "load_opta_event_data",
    "to_pandas",
    "transform",
]
