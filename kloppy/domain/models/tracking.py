from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union, TYPE_CHECKING

from kloppy.domain.models.common import DatasetType
from kloppy.utils import (
    deprecated,
    docstring_inherit_attributes,
)

if TYPE_CHECKING:
    from kloppy.io import FileLike, open_as_file

from .common import DataRecord, Dataset, Player
from .pitch import Point, Point3D

if TYPE_CHECKING:
    from pandas import DataFrame


@dataclass
class PlayerData:
    coordinates: Point
    distance: Optional[float] = None
    speed: Optional[float] = None
    other_data: dict[str, Any] = field(default_factory=dict)


@docstring_inherit_attributes(DataRecord)
@dataclass(repr=False)
class Frame(DataRecord):
    """
    Tracking data frame.

    Attributes:
        frame_id: The unique identifier of the frame. Aias for `record_id`.
        ball_coordinates: The coordinates of the ball
        players_data: A dictionary containing the tracking data for each player.
        ball_speed: The speed of the ball
        other_data: A dictionary containing additional data
    """

    frame_id: int
    players_data: dict[Player, PlayerData]
    other_data: dict[str, Any]
    ball_coordinates: Point3D
    ball_speed: Optional[float] = None

    @property
    def record_id(self) -> int:
        return self.frame_id

    @property
    def players_coordinates(self):
        return {
            player: player_data.coordinates
            for player, player_data in self.players_data.items()
        }

    def __str__(self):
        return f"<{self.__class__.__name__} frame_id='{self.frame_id}' time='{self.time}'>"

    def __repr__(self):
        return str(self)


@dataclass
@docstring_inherit_attributes(Dataset)
class TrackingDataset(Dataset[Frame]):
    """
    A tracking dataset.

    Attributes:
        dataset_type (DatasetType): `"DatasetType.TRACKING"`
        frames (List[Frame]): A list of frames. Alias for `records`.
        frame_rate (float): The frame rate (in Hertz) at which the data was recorded.
        metadata (Metadata): Metadata of the tracking dataset.
    """

    dataset_type: DatasetType = DatasetType.TRACKING

    @property
    def frames(self):
        return self.records

    @property
    def frame_rate(self):
        return self.metadata.frame_rate

    @deprecated(
        "to_pandas will be removed in the future. Please use to_df instead."
    )
    def to_pandas(
        self,
        record_converter: Optional[Callable[[Frame], dict]] = None,
        additional_columns=None,
    ) -> "DataFrame":  # noqa: F821
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Seems like you don't have pandas installed. Please"
                " install it using: pip install pandas"
            )

        if not record_converter:
            from ..services.transformers.attribute import (
                DefaultFrameTransformer,
            )

            record_converter = DefaultFrameTransformer()

        def generic_record_converter(frame: Frame):
            row = record_converter(frame)
            if additional_columns:
                for k, v in additional_columns.items():
                    if callable(v):
                        value = v(frame)
                    else:
                        value = v
                    row.update({k: value})

            return row

        return pd.DataFrame.from_records(
            map(generic_record_converter, self.records)
        )

    # Update the to_cdf method in Dataset class
    def to_cdf(
        self,
        metadata_output_file: "FileLike",
        tracking_output_file: "FileLike",
        additional_metadata: Optional[Union[dict, "CdfMetaDataSchema"]] = None,
    ) -> None:
        """
        Export dataset to Common Data Format (CDF).

        Args:
            metadata_output_file: File path or file-like object for metadata JSON output.
                Must have .json extension if a string path.
            tracking_output_file: File path or file-like object for tracking JSONL output.
                Must have .jsonl extension if a string path.
            additional_metadata: Additional metadata to include in the CDF output.
                Can be a complete CdfMetaDataSchema TypedDict or a partial dict.
                Supported top-level keys: 'competition', 'season', 'stadium', 'meta', 'match'.
                Supports nested updates like {'stadium': {'id': '123'}}.

        Raises:
            KloppyError: If the dataset is not a TrackingDataset.
            ValueError: If file extensions are invalid.

        Examples:
            >>> # Export to local files
            >>> dataset.to_cdf(
            ...     metadata_output_file='metadata.json',
            ...     tracking_output_file='tracking.jsonl'
            ... )

            >>> # Export to S3
            >>> dataset.to_cdf(
            ...     metadata_output_file='s3://bucket/metadata.json',
            ...     tracking_output_file='s3://bucket/tracking.jsonl'
            ... )

            >>> # Export with partial metadata updates
            >>> dataset.to_cdf(
            ...     metadata_output_file='metadata.json',
            ...     tracking_output_file='tracking.jsonl',
            ...     additional_metadata={
            ...         'competition': {'id': '123'},
            ...         'season': {'id': '2024'},
            ...         'stadium': {'id': '456', 'name': 'Stadium Name'}
            ...     }
            ... )
        """
        from kloppy.domain import DatasetType
        from kloppy.exceptions import KloppyError
        from kloppy.infra.serializers.tracking.cdf import (
            CDFTrackingSerializer,
            CDFOutputs,
        )
        from kloppy.io import FileLike, open_as_file

        serializer = CDFTrackingSerializer()

        # TODO: write files but also support non-local files, similar to how open_as_file supports non-local files

        # Use open_as_file with mode="wb" for writing
        with open_as_file(
            metadata_output_file, mode="wb"
        ) as metadata_fp, open_as_file(
            tracking_output_file, mode="wb"
        ) as tracking_fp:
            serializer.serialize(
                dataset=self,
                outputs=CDFOutputs(
                    meta_data=metadata_fp, raw_data=tracking_fp
                ),
                additional_metadata=additional_metadata,
            )


__all__ = ["Frame", "TrackingDataset", "PlayerData"]
