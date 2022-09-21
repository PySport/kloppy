from typing import Optional, List, Union

from kloppy.config import get_config
from kloppy.domain import EventDataset, TrackingDataset, EventFactory
from kloppy.exceptions import KloppyError
from kloppy.infra.serializers.event.metrica import (
    MetricaJsonEventDataDeserializer,
    MetricaJsonEventDataInputs,
)
from kloppy.infra.serializers.tracking.metrica_csv import (
    MetricaCSVTrackingDataDeserializer,
    MetricaCSVTrackingDataInputs,
)
from kloppy.infra.serializers.tracking.metrica_epts import (
    MetricaEPTSTrackingDataDeserializer,
    MetricaEPTSTrackingDataInputs,
)
from kloppy.io import FileLike, open_as_file


def load_tracking_csv(
    home_data: FileLike,
    away_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
) -> TrackingDataset:
    deserializer = MetricaCSVTrackingDataDeserializer(
        sample_rate=sample_rate, limit=limit, coordinate_system=coordinates
    )
    with open_as_file(home_data) as home_data_fp, open_as_file(
        away_data
    ) as away_data_fp:
        return deserializer.deserialize(
            inputs=MetricaCSVTrackingDataInputs(
                home_data=home_data_fp, away_data=away_data_fp
            )
        )


def load_tracking_epts(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
) -> TrackingDataset:
    deserializer = MetricaEPTSTrackingDataDeserializer(
        sample_rate=sample_rate, limit=limit, coordinate_system=coordinates
    )
    with open_as_file(raw_data) as raw_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return deserializer.deserialize(
            inputs=MetricaEPTSTrackingDataInputs(
                raw_data=raw_data_fp, meta_data=meta_data_fp
            )
        )


def load_event(
    event_data: FileLike,
    meta_data: FileLike,
    event_types: Optional[List[str]] = None,
    coordinates: Optional[str] = None,
    event_factory: Optional[EventFactory] = None,
) -> EventDataset:
    deserializer = MetricaJsonEventDataDeserializer(
        event_types=event_types,
        coordinate_system=coordinates,
        event_factory=event_factory or get_config("event_factory"),
    )

    with open_as_file(event_data) as event_data_fp, open_as_file(
        meta_data
    ) as meta_data_fp:
        return deserializer.deserialize(
            inputs=MetricaJsonEventDataInputs(
                event_data=event_data_fp, meta_data=meta_data_fp
            )
        )


def load_open_data(
    match_id: Union[str, int] = "1",
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
) -> TrackingDataset:
    if match_id == "1" or match_id == 1:
        return load_tracking_csv(
            home_data="https://raw.githubusercontent.com/metrica-sports/sample-data/"
            "master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv",
            away_data="https://raw.githubusercontent.com/metrica-sports/sample-data/"
            "master/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Away_Team.csv",
            sample_rate=sample_rate,
            limit=limit,
            coordinates=coordinates,
        )
    elif match_id == "2" or match_id == 2:
        return load_tracking_csv(
            home_data="https://raw.githubusercontent.com/metrica-sports/sample-data/"
            "master/data/Sample_Game_2/Sample_Game_2_RawTrackingData_Home_Team.csv",
            away_data="https://raw.githubusercontent.com/metrica-sports/sample-data/"
            "master/data/Sample_Game_2/Sample_Game_2_RawTrackingData_Away_Team.csv",
            sample_rate=sample_rate,
            limit=limit,
            coordinates=coordinates,
        )
    elif match_id == "3" or match_id == 3:
        return load_tracking_epts(
            meta_data="https://raw.githubusercontent.com/metrica-sports/sample-data/"
            "master/data/Sample_Game_3/Sample_Game_3_metadata.xml",
            raw_data="https://raw.githubusercontent.com/metrica-sports/sample-data/"
            "master/data/Sample_Game_3/Sample_Game_3_tracking.txt",
            sample_rate=sample_rate,
            limit=limit,
            coordinates=coordinates,
        )
    else:
        raise KloppyError(
            f"Don't know where to fetch Metrica open data for {match_id}"
        )
