from typing import Callable, Dict, List, TypeVar, Union, Any

from . import (
    EPTSSerializer,
    MetricaEventsJsonSerializer,
    MetricaTrackingSerializer,
    OptaSerializer,
    SportecEventSerializer,
    SkillCornerTrackingSerializer,
    StatsBombSerializer,
    TRACABSerializer,
    WyscoutSerializer,
    XMLCodeSerializer,
)
from .domain import (
    CardEvent,
    CarryEvent,
    DataRecord,
    Dataset,
    Dimension,
    Event,
    EventDataset,
    EventType,
    Frame,
    Orientation,
    PassEvent,
    PassResult,
    PitchDimensions,
    ShotEvent,
    TrackingDataset,
    Transformer,
    Provider,
    build_coordinate_system,
    CodeDataset,
    Code,
    CoordinateSystem,
)


def load_tracab_tracking_data(
    metadata_filename: str, raw_data_filename: str, options: dict = None
) -> TrackingDataset:
    serializer = TRACABSerializer()
    with open(metadata_filename, "rb") as metadata, open(
        raw_data_filename, "rb"
    ) as raw_data:

        return serializer.deserialize(
            inputs={"metadata": metadata, "raw_data": raw_data},
            options=options,
        )


def load_skillcorner_tracking_data(
    metadata_filename: str, raw_data_filename: str, options: dict = None
) -> TrackingDataset:
    serializer = SkillCornerTrackingSerializer()
    with open(metadata_filename, "rb") as metadata, open(
        raw_data_filename, "rb"
    ) as raw_data:

        return serializer.deserialize(
            inputs={"metadata": metadata, "raw_data": raw_data},
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
    metadata_filename: str, raw_data_filename: str, options: dict = None
) -> TrackingDataset:
    serializer = EPTSSerializer()
    with open(metadata_filename, "rb") as metadata, open(
        raw_data_filename, "rb"
    ) as raw_data:

        return serializer.deserialize(
            inputs={"metadata": metadata, "raw_data": raw_data},
            options=options,
        )


def load_statsbomb_event_data(
    event_data_filename: str, lineup_data_filename: str, options: dict = None
) -> EventDataset:
    """
    Load Statsbomb event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data_filename: filename of json containing the events
        lineup_data_filename: filename of json containing the lineup information
        options:
    """
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
    """
    Load Opta event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        f24_data_filename: filename of the f24 XML file containing the events
        f7_data_filename: filename of the f7 XML file containing metadata
        options:
    """
    serializer = OptaSerializer()
    with open(f24_data_filename, "rb") as f24_data, open(
        f7_data_filename, "rb"
    ) as f7_data:

        return serializer.deserialize(
            inputs={"f24_data": f24_data, "f7_data": f7_data},
            options=options,
        )


def load_metrica_json_event_data(
    raw_data_filename: str, metadata_filename: str, options: dict = None
) -> EventDataset:
    """
    Load Metrica event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        raw_data_filename: filename of the json file containing the events
        metadata_filename: filename of the EPTS XML file containing metadata
        options:
    """
    serializer = MetricaEventsJsonSerializer()
    with open(metadata_filename, "rb") as metadata, open(
        raw_data_filename, "rb"
    ) as raw_data:

        return serializer.deserialize(
            inputs={"metadata": metadata, "event_data": raw_data},
            options=options,
        )


def load_sportec_event_data(
    event_data_filename: str, match_data_filename: str, options: dict = None
) -> EventDataset:
    """
    Load Sportec event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data_filename: filename of the XML file containing the events
        match_data_filename: filename of the XML file containing the match information
        options:
    """
    serializer = SportecEventSerializer()
    with open(event_data_filename, "rb") as event_data, open(
        match_data_filename, "rb"
    ) as match_data:

        return serializer.deserialize(
            inputs={"event_data": event_data, "match_data": match_data},
            options=options,
        )


def load_wyscout_event_data(
    event_data_filename: str, options: dict = None
) -> EventDataset:
    """
    Load Wyscout event data into a [`EventDataset`][kloppy.domain.models.event.EventDataset]

    Parameters:
        event_data_filename: filename of the XML file containing the events and metadata
        options:
    """
    serializer = WyscoutSerializer()
    with open(event_data_filename, "rb") as event_data:
        return serializer.deserialize(
            inputs={"event_data": event_data}, options=options
        )


def load_xml_code_data(xml_filename: str) -> CodeDataset:
    serializer = XMLCodeSerializer()
    with open(xml_filename, "rb") as xml_file:
        return serializer.deserialize(inputs={"xml_file": xml_file})


def write_xml_code_data(dataset: CodeDataset, xml_filename: str):
    serializer = XMLCodeSerializer()
    with open(xml_filename, "wb") as xml_file:
        content = serializer.serialize(dataset)
        xml_file.write(content)


DatasetT = TypeVar("DatasetT")


def transform(
    dataset: Dataset,
    to_orientation=None,
    to_pitch_dimensions=None,
    to_coordinate_system: Union[CoordinateSystem, Provider] = None,
) -> Dataset:

    if to_pitch_dimensions and to_coordinate_system:
        raise ValueError(
            "You can't do both a PitchDimension and CoordinateSysetm on the same dataset transformation"
        )

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

    if to_coordinate_system and isinstance(to_coordinate_system, Provider):
        to_coordinate_system = build_coordinate_system(
            provider=to_coordinate_system,
            length=dataset.metadata.coordinate_system.length,
            width=dataset.metadata.coordinate_system.width,
        )

        return Transformer.transform_dataset(
            dataset=dataset,
            to_orientation=to_orientation,
            to_coordinate_system=to_coordinate_system,
        )


def _frame_to_pandas_row_converter(frame: Frame) -> Dict:
    row = dict(
        period_id=frame.period.id if frame.period else None,
        timestamp=frame.timestamp,
        ball_state=frame.ball_state.value if frame.ball_state else None,
        ball_owning_team_id=frame.ball_owning_team.team_id
        if frame.ball_owning_team
        else None,
        ball_x=frame.ball_coordinates.x if frame.ball_coordinates else None,
        ball_y=frame.ball_coordinates.y if frame.ball_coordinates else None,
    )
    for player, coordinates in frame.players_coordinates.items():
        row.update(
            {
                f"{player.player_id}_x": coordinates.x,
                f"{player.player_id}_y": coordinates.y,
            }
        )

    return row


def _event_to_pandas_row_converter(event: Event) -> Dict:
    row = dict(
        event_id=event.event_id,
        event_type=(
            event.event_type.value
            if event.event_type != EventType.GENERIC
            else f"GENERIC:{event.event_name}"
        ),
        result=event.result.value if event.result else None,
        success=event.result.is_success if event.result else None,
        period_id=event.period.id,
        timestamp=event.timestamp,
        end_timestamp=None,
        ball_state=event.ball_state.value if event.ball_state else None,
        ball_owning_team=event.ball_owning_team.team_id
        if event.ball_owning_team
        else None,
        team_id=event.team.team_id if event.team else None,
        player_id=event.player.player_id if event.player else None,
        coordinates_x=event.coordinates.x if event.coordinates else None,
        coordinates_y=event.coordinates.y if event.coordinates else None,
    )
    if isinstance(event, PassEvent) and event.result == PassResult.COMPLETE:
        row.update(
            {
                "end_timestamp": event.receive_timestamp,
                "end_coordinates_x": event.receiver_coordinates.x
                if event.receiver_coordinates
                else None,
                "end_coordinates_y": event.receiver_coordinates.y
                if event.receiver_coordinates
                else None,
                "receiver_player_id": event.receiver_player.player_id
                if event.receiver_player
                else None,
            }
        )
    elif isinstance(event, CarryEvent):
        row.update(
            {
                "end_timestamp": event.end_timestamp,
                "end_coordinates_x": event.end_coordinates.x
                if event.end_coordinates
                else None,
                "end_coordinates_y": event.end_coordinates.y
                if event.end_coordinates
                else None,
            }
        )
    elif isinstance(event, ShotEvent):
        row.update(
            {
                "end_coordinates_x": event.result_coordinates.x
                if event.result_coordinates
                else None,
                "end_coordinates_y": event.result_coordinates.y
                if event.result_coordinates
                else None,
            }
        )
    elif isinstance(event, CardEvent):
        row.update(
            {"card_type": event.card_type.value if event.card_type else None}
        )

    if event.qualifiers:
        for qualifier in event.qualifiers:
            row.update(qualifier.to_dict())

    return row


def _code_to_pandas_row_converter(code: Code) -> Dict:
    row = dict(
        code_id=code.code_id,
        period_id=code.period.id if code.period else None,
        timestamp=code.timestamp,
        end_timestamp=code.end_timestamp,
        code=code.code,
    )
    row.update(code.labels)

    return row


def to_pandas(
    dataset: Union[Dataset, List[DataRecord]],
    _record_converter: Callable[[DataRecord], Dict] = None,
    additional_columns: Dict[
        str, Union[Callable[[DataRecord], Any], Any]
    ] = None,
) -> "DataFrame":
    """
    Convert Dataset to a pandas dataframe

    Arguments:
        dataset: Dataset to operate on. Don't pass this argument when you do dataset.to_pandas()
        _record_converter: Custom converter to go from record to DataRecord to Dict
        additional_columns: Additional columns to add to the dataframe

    Examples:
        >>> dataframe = dataset.to_pandas(additional_columns={
        >>>    'player_name': lambda event: event.player.name
        >>> })
    """
    try:
        import pandas as pd
    except ImportError:
        raise Exception(
            "Seems like you don't have pandas installed. Please"
            " install it using: pip install pandas"
        )

    if isinstance(dataset, Dataset):
        records = dataset.records
    elif isinstance(dataset, list):
        records = dataset
    else:
        raise Exception("Unknown dataset type")

    if not records:
        return pd.DataFrame()

    if not _record_converter:
        if isinstance(dataset, TrackingDataset) or isinstance(
            records[0], Frame
        ):
            _record_converter = _frame_to_pandas_row_converter
        elif isinstance(dataset, EventDataset) or isinstance(
            records[0], Event
        ):
            _record_converter = _event_to_pandas_row_converter
        elif isinstance(dataset, CodeDataset) or isinstance(records[0], Code):
            _record_converter = _code_to_pandas_row_converter
        else:
            raise Exception("Don't know how to convert rows")

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

    return pd.DataFrame.from_records(map(generic_record_converter, records))


__all__ = [
    "load_tracab_tracking_data",
    "load_skillcorner_tracking_data",
    "load_metrica_tracking_data",
    "load_metrica_json_event_data",
    "load_epts_tracking_data",
    "load_statsbomb_event_data",
    "load_opta_event_data",
    "load_sportec_event_data",
    "load_wyscout_event_data",
    "load_xml_code_data",
    "write_xml_code_data",
    "to_pandas",
    "transform",
]
