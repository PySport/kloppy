from kloppy.infra.serializers.tracking.pff_fc import (
    PFF_FCTrackingInputs, PFF_FCTrackingDeserializer
)

from kloppy.domain import Optional, TrackingDataset
from kloppy.io import open_as_file, FileLike

def load_tracking(
    meta_data: FileLike,
    players_meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    include_empty_frames: Optional[bool] = False,
) -> TrackingDataset:
    deserializer = PFF_FCTrackingDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        include_empty_frames=include_empty_frames,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(players_meta_data) as players_meta_data_fp:
        return deserializer.deserialize(
            inputs=PFF_FCTrackingInputs(
                meta_data=meta_data_fp, players_meta_data=players_meta_data_fp, raw_data=raw_data
            )
        )