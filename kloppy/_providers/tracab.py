import warnings
from typing import Optional

from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.tracab.deserializer import (
    TRACABDeserializer,
    TRACABInputs,
)
from kloppy.io import FileLike, open_as_file


def load(
    meta_data: FileLike,
    raw_data: FileLike,
    sample_rate: Optional[float] = None,
    limit: Optional[int] = None,
    coordinates: Optional[str] = None,
    only_alive: bool = True,
    file_format: Optional[str] = None,
) -> TrackingDataset:
    """
    Load TRACAB tracking data.

    Args:
        meta_data: A JSON or XML feed containing the meta data.
        raw_data: A JSON or dat feed containing the raw tracking data.
        sample_rate: Sample the data at a specific rate.
        limit: Limit the number of frames to load to the first `limit` frames.
        coordinates: The coordinate system to use.
        only_alive: Only include frames in which the game is not paused.
        file_format: Deprecated. The format will be inferred based on the file extensions.

    Returns:
        The parsed tracking data.

    Notes:
        Tracab distributes its metadata in various formats. Kloppy tries to
        infer automatically which format applies. Currently, kloppy supports
        the following formats:

        - **Flat XML structure**:

            <root>
                <GameID>13331</GameID>
                <CompetitionID>55</CompetitionID>
                ...
            </root>

        - **Hierarchical XML structure**:

            <match iId="1" ...>
                <period iId="1" iStartFrame="1848508" iEndFrame="1916408"/>
                ...
            </match>

        - **JSON structure**:

            {
                "GameID": 1,
                "CompetitionID": 1,
                "SeasonID": 2023,
                ...
            }

        If parsing fails for a supported format or you encounter an unsupported
        structure, please create an issue on the kloppy GitHub repository
        with a sample of the problematic data.
    """
    # file format is deprecated
    if file_format is not None:
        warnings.warn(
            "file_format is deprecated. This is now automatically infered.",
            DeprecationWarning,
            stacklevel=2,
        )

    deserializer = TRACABDeserializer(
        sample_rate=sample_rate,
        limit=limit,
        coordinate_system=coordinates,
        only_alive=only_alive,
    )
    with open_as_file(meta_data) as meta_data_fp, open_as_file(
        raw_data
    ) as raw_data_fp:
        return deserializer.deserialize(
            inputs=TRACABInputs(meta_data=meta_data_fp, raw_data=raw_data_fp)
        )
