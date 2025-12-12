import json
import tempfile
from typing import IO, NamedTuple, Optional, Union, TYPE_CHECKING

from kloppy.domain import (
    Provider,
    TrackingDataset,
    Orientation,
    BallState,
    CDFCoordinateSystem,
    Ground,
)
from kloppy.infra.serializers.tracking.serializer import TrackingDataSerializer

from .helpers import (
    PERIODS_MAP,
    get_player_coordinates,
    get_ball_coordinates,
    initialize_period_tracking,
    update_period_tracking,
    get_starters_and_formation,
    build_periods_info,
    build_whistles,
    build_team_players_metadata,
)

if TYPE_CHECKING:
    from cdf.domain.latest.meta import (
        CdfMetaDataSchema,
        Stadium,
        Competition,
        Season,
        Meta,
        Misc,
    )

import warnings

MISSING_MANDATORY_ID = "MISSING_MANDATORY_ID"


class CDFOutputs(NamedTuple):
    meta_data: IO[bytes]
    tracking_data: IO[bytes]


class CDFTrackingDataSerializer(TrackingDataSerializer[CDFOutputs]):
    provider = Provider.CDF

    def serialize(
        self,
        dataset: TrackingDataset,
        outputs: CDFOutputs,
        additional_metadata: Optional[
            Union[
                "CdfMetaDataSchema",
                "Stadium",
                "Competition",
                "Season",
                "Meta",
                "Misc",
                dict,
            ]
        ] = None,
    ) -> bool:
        """
        Serialize a TrackingDataset to Common Data Format.

        Args:
            dataset: The tracking dataset to serialize
            outputs: CDFOutputs containing file handles for metadata and tracking data
            additional_metadata: Either a complete CdfMetaDataSchema or partial metadata
                dict containing any of: 'competition', 'season', 'stadium', 'meta', 'misc'.
                Can also contain direct field updates like {'stadium': {'id': '123'}}.

        Returns:
            bool: True if serialization was successful
        """
        if all(
            True if x.ball_state == BallState.ALIVE else False for x in dataset
        ):
            warnings.warn(
                "All frames in 'tracking_dataset' are 'ALIVE', the Common Data Format expects 'DEAD' frames as well. Set `only_alive=False` in your kloppy `.load_tracking()` call to include 'DEAD' frames.",
                UserWarning,
            )

        dataset = dataset.transform(
            to_coordinate_system=CDFCoordinateSystem(
                dataset.metadata.coordinate_system
            ),
            to_orientation=Orientation.STATIC_HOME_AWAY,
        )

        period_tracking = initialize_period_tracking(dataset.metadata.periods)
        self._home_team, self._away_team = dataset.metadata.teams

        self._serialize_tracking_frames(
            dataset,
            outputs,
            period_tracking,
        )

        self._serialize_metadata(
            dataset,
            outputs,
            period_tracking,
            additional_metadata or {},
        )

        return True

    def _serialize_tracking_frames(self, dataset, outputs, period_tracking):
        """Serialize tracking data frames to JSONL format.

        Iterates through all frames in the dataset and writes each frame's tracking
        data (player positions, ball coordinates, timestamps) directly to the output
        JSONL file.

        Args:
            dataset: The kloppy tracking dataset containing frames to serialize.
            outputs: CDFOutputs object containing the tracking data file handle.
            period_tracking: Dictionary containing period frame ID tracking information.
        """
        for frame in dataset.frames:
            period_id = frame.period.id
            ball_status = frame.ball_state == BallState.ALIVE

            normalized_frame_id = update_period_tracking(
                period_tracking, period_id, frame.frame_id
            )

            home_players = get_player_coordinates(frame, Ground.HOME)
            away_players = get_player_coordinates(frame, Ground.AWAY)

            if period_id not in PERIODS_MAP:
                raise ValueError(
                    f"Incorrect period_id {period_id}. Period ID {period_id} this is not supported by the Common Data Format"
                )

            frame_data = {
                "frame_id": normalized_frame_id,
                "original_frame_id": frame.frame_id,
                "timestamp": str(dataset.metadata.date + frame.timestamp),
                "period": PERIODS_MAP[period_id],
                "match": {"id": str(dataset.metadata.game_id)},
                "ball_status": ball_status,
                "teams": {
                    "home": {
                        "id": str(self._home_team.team_id),
                        "players": home_players,
                        "name": self._home_team.name,
                    },
                    "away": {
                        "id": str(self._away_team.team_id),
                        "players": away_players,
                        "name": self._away_team.name,
                    },
                },
                "ball": get_ball_coordinates(frame),
            }

            outputs.tracking_data.write(
                (json.dumps(frame_data) + "\n").encode("utf-8")
            )

    def _build_default_metadata_structure(
        self,
        dataset,
        period_tracking,
    ) -> "CdfMetaDataSchema":
        """Build default CDF metadata structure from dataset."""
        first_frame = dataset[0]

        home_starters, home_formation = get_starters_and_formation(
            self._home_team, first_frame
        )
        away_starters, away_formation = get_starters_and_formation(
            self._away_team, first_frame
        )

        periods_info = build_periods_info(
            dataset, period_tracking, self._home_team, self._away_team
        )

        whistles = build_whistles(periods_info)

        return {
            "competition": {
                "id": MISSING_MANDATORY_ID,
            },
            "season": {
                "id": MISSING_MANDATORY_ID,
            },
            "stadium": {
                "id": MISSING_MANDATORY_ID,
                "pitch_length": dataset.metadata.pitch_dimensions.pitch_length,
                "pitch_width": dataset.metadata.pitch_dimensions.pitch_width,
            },
            "match": {
                "id": str(dataset.metadata.game_id),
                "kickoff_time": str(
                    dataset.metadata.date
                    + dataset.metadata.periods[0].start_timestamp
                ),
                "periods": periods_info,
                "whistles": whistles,
                "scheduled_kickoff_time": str(dataset.metadata.date),
            },
            "teams": {
                "home": {
                    "id": self._home_team.team_id,
                    "players": build_team_players_metadata(
                        self._home_team, home_starters
                    ),
                    "name": self._home_team.name,
                    "formation": home_formation,
                },
                "away": {
                    "id": self._away_team.team_id,
                    "players": build_team_players_metadata(
                        self._away_team, away_starters
                    ),
                    "name": self._away_team.name,
                    "formation": away_formation,
                },
            },
            "meta": {
                "video": None,
                "tracking": None,
                "landmarks": None,
                "ball": None,
                "meta": None,
                "cdf": None,
                "event": None,
            },
        }

    def _deep_merge_metadata(self, base: dict, updates: dict) -> dict:
        """
        Deep merge metadata updates into base metadata.

        Args:
            base: Base metadata dictionary
            updates: Updates to apply (can be nested)

        Returns:
            Merged metadata dictionary
        """
        result = base.copy()

        for key, value in updates.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge_metadata(result[key], value)
            else:
                result[key] = value

        return result

    def _internal_validation_metadata(
        self, metadata: dict, path: str = ""
    ) -> None:
        """
        Validate metadata and warn about missing mandatory IDs.

        Args:
            metadata: Metadata dictionary to validate
            path: Current path in the metadata structure (for nested dicts)
        """
        for key, value in metadata.items():
            current_path = f"{path}.{key}" if path else key

            if value == MISSING_MANDATORY_ID:
                warnings.warn(
                    f"Missing mandatory ID at '{current_path}'. Currently replaced with the value '{MISSING_MANDATORY_ID}'. "
                    f"Please provide the correct value to 'additional_metadata' to completely adhere to the CDF specification.",
                    UserWarning,
                )
            elif isinstance(value, dict):
                self._internal_validation_metadata(value, current_path)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._internal_validation_metadata(
                            item, f"{current_path}[{i}]"
                        )

    def _serialize_metadata(
        self,
        dataset,
        outputs,
        period_tracking,
        additional_metadata: dict,
    ):
        """
        Serialize metadata to JSON format.

        Builds and writes the complete metadata JSON including competition, season,
        match information, periods, whistles, team rosters with formations, and
        stadium dimensions. Accepts additional metadata for overrides.

        Args:
            dataset: The tracking dataset containing metadata to serialize.
            outputs: CDFOutputs object containing the metadata file handle.
            period_tracking: Dictionary containing normalized period frame IDs.
            additional_metadata: Additional or override metadata following CdfMetaDataSchema.
        """
        metadata_json = self._build_default_metadata_structure(
            dataset, period_tracking
        )

        if additional_metadata:
            metadata_json = self._deep_merge_metadata(
                metadata_json, additional_metadata
            )

        self._internal_validation_metadata(metadata_json)

        outputs.meta_data.write(
            (json.dumps(metadata_json) + "\n").encode("utf-8")
        )
