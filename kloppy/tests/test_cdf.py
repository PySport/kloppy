import tempfile
from pathlib import Path

import pytest
import cdf

import json
import warnings

from kloppy import sportec, skillcorner
from kloppy.domain import TrackingDataset, PositionType
from kloppy.infra.serializers.tracking.cdf.serializer import (
    CDFTrackingDataSerializer,
    CDFOutputs,
)
from kloppy.infra.serializers.tracking.cdf.helpers import (
    is_valid_cdf_position_code,
)


class TestCDFSerializer:
    @pytest.fixture
    def raw_data(self, base_dir) -> Path:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/sportec_meta.xml"

    @pytest.fixture
    def meta_data_v3(self, base_dir) -> str:
        return base_dir / "files/skillcorner_meta_data.json"

    @pytest.fixture
    def raw_data_v3(self, base_dir) -> str:
        return base_dir / "files/skillcorner_v3_raw_data.jsonl"

    @pytest.fixture
    def dataset(self, raw_data: Path, meta_data: Path) -> TrackingDataset:
        """Load a small Sportec tracking data snippet for testing CDF serialization."""
        return sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            limit=None,
            only_alive=False,
        )

    @pytest.fixture
    def test_correct_deserialization_v3(
        self, raw_data_v3: Path, meta_data_v3: Path
    ):
        return skillcorner.load(
            meta_data=meta_data_v3,
            raw_data=raw_data_v3,
            coordinates="skillcorner",
            include_empty_frames=True,
            only_alive=False,
        )

    def test_produces_valid_cdf_output(self, dataset):
        """Test that CDFTrackingDataSerializer produces valid CDF output."""
        serializer = CDFTrackingDataSerializer()

        # Instantiate Validators
        meta_validator = cdf.MetaSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/meta.json"
        )
        tracking_validator = cdf.TrackingSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/tracking.json"
        )

        with tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".json", delete=False
        ) as meta_file, tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".jsonl", delete=False
        ) as tracking_file:

            # Instantiate the named tuple for outputs
            outputs = CDFOutputs(
                meta_data=meta_file, tracking_data=tracking_file
            )

            # Serialize the dataset and capture warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                success = serializer.serialize(dataset, outputs)
                assert success is True

                # Verify warnings about missing mandatory IDs were raised
                missing_id_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, UserWarning)
                    and "Missing mandatory ID" in str(warning.message)
                ]

                # Should have warnings for competition.id, season.id, and stadium.id
                assert len(missing_id_warnings) == 3, (
                    f"Expected 3 missing mandatory ID warnings, but got {len(missing_id_warnings)}: "
                    f"{[str(warning.message) for warning in missing_id_warnings]}"
                )

                # Check specific warnings are present
                warning_messages = [
                    str(warning.message) for warning in missing_id_warnings
                ]
                assert any(
                    "competition.id" in msg for msg in warning_messages
                ), "Missing warning for competition.id"
                assert any(
                    "season.id" in msg for msg in warning_messages
                ), "Missing warning for season.id"
                assert any(
                    "stadium.id" in msg for msg in warning_messages
                ), "Missing warning for stadium.id"

            # Save paths for validation after leaving the block
            meta_path = meta_file.name
            tracking_path = tracking_file.name

        # Validate metadata
        meta_validator.validate_schema(sample=meta_path)

        # Validate tracking data - read and validate each line (frame) in the JSONL file
        with open(tracking_path, "r") as f:
            frame_count = 0
            for line in f:
                if line.strip():  # Skip empty lines
                    frame_data = json.loads(line)
                    # Validate each frame against the tracking schema
                    tracking_validator.validate_schema(sample=frame_data)
                    frame_count += 1

        assert frame_count > 0, "No frames were serialized"

        # Clean up
        Path(meta_path).unlink()
        Path(tracking_path).unlink()

    def test_produces_valid_cdf_output_with_additional_metadata(self, dataset):
        """Test that CDFTrackingDataSerializer produces valid CDF output with additional metadata."""
        serializer = CDFTrackingDataSerializer()

        # Instantiate Validators
        meta_validator = cdf.MetaSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/meta.json"
        )
        tracking_validator = cdf.TrackingSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/tracking.json"
        )

        # Define additional metadata
        additional_metadata = {
            "competition": {
                "id": "COMP_123",
                "name": "Test Competition",
                "format": "league_20",
            },
            "season": {"id": "SEASON_2024", "name": "2024/25"},
            "stadium": {
                "id": "STADIUM_456",
                "name": "Test Arena",
                "turf": "grass",
            },
            "meta": {
                "tracking": {
                    "version": "2.0.0",
                    "name": "TestTracker",
                    "fps": 30,
                    "collection_timing": "live",
                }
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".json", delete=False
        ) as meta_file, tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".jsonl", delete=False
        ) as tracking_file:

            # Instantiate the named tuple for outputs
            outputs = CDFOutputs(
                meta_data=meta_file, tracking_data=tracking_file
            )

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                success = serializer.serialize(
                    dataset, outputs, additional_metadata=additional_metadata
                )
                assert success is True

                # Verify no warnings about missing mandatory IDs were raised
                missing_id_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, UserWarning)
                    and "Missing mandatory ID" in str(warning.message)
                ]
                assert len(missing_id_warnings) == 0, (
                    f"Expected no missing mandatory ID warnings, but got {len(missing_id_warnings)}: "
                    f"{[str(warning.message) for warning in missing_id_warnings]}"
                )

            # Save paths for validation after leaving the block
            meta_path = meta_file.name
            tracking_path = tracking_file.name

        # Validate metadata
        meta_validator.validate_schema(sample=meta_path)

        # Verify additional metadata was applied correctly
        with open(meta_path, "r") as f:
            meta_data = json.load(f)

            # Check competition metadata
            assert meta_data["competition"]["id"] == "COMP_123"
            assert meta_data["competition"]["name"] == "Test Competition"
            assert meta_data["competition"]["format"] == "league_20"

            # Check season metadata
            assert meta_data["season"]["id"] == "SEASON_2024"
            assert meta_data["season"]["name"] == "2024/25"

            # Check stadium metadata
            assert meta_data["stadium"]["id"] == "STADIUM_456"
            assert meta_data["stadium"]["name"] == "Test Arena"
            assert meta_data["stadium"]["turf"] == "grass"
            # Verify default values still present
            assert "pitch_length" in meta_data["stadium"]
            assert "pitch_width" in meta_data["stadium"]

            # Check meta tracking information
            assert meta_data["meta"]["tracking"]["version"] == "2.0.0"
            assert meta_data["meta"]["tracking"]["name"] == "TestTracker"
            assert meta_data["meta"]["tracking"]["fps"] == 30
            assert meta_data["meta"]["tracking"]["collection_timing"] == "live"

        # Validate tracking data - read and validate each line (frame) in the JSONL file
        with open(tracking_path, "r") as f:
            frame_count = 0
            for line in f:
                if line.strip():  # Skip empty lines
                    frame_data = json.loads(line)
                    # Validate each frame against the tracking schema
                    tracking_validator.validate_schema(sample=frame_data)
                    frame_count += 1

        assert frame_count > 0, "No frames were serialized"

        # Clean up
        Path(meta_path).unlink()
        Path(tracking_path).unlink()

    def test_serializer_handles_invalid_metadata_types(self, dataset):
        """Test that CDFTrackingDataSerializer handles invalid metadata types gracefully."""
        serializer = CDFTrackingDataSerializer()

        with tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".json", delete=False
        ) as meta_file, tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".jsonl", delete=False
        ) as tracking_file:

            meta_path = meta_file.name
            tracking_path = tracking_file.name

            outputs = CDFOutputs(
                meta_data=meta_file, tracking_data=tracking_file
            )

            # Test with invalid metadata types - should still serialize but may fail validation
            invalid_metadata = {
                "competition": {
                    "id": 123,  # Should be string
                },
                "season": {
                    "id": ["2024"],  # Should be string, not list
                },
                "stadium": {
                    "id": None,  # Should be string
                    "pitch_length": "one hundred five",  # Should be float/int
                },
                "meta": {
                    "tracking": {
                        "fps": "25",  # Should be int
                        "version": 1.0,  # Should be string
                    }
                },
            }

            # Serialization should succeed (no type checking in serializer)
            success = serializer.serialize(
                dataset, outputs, additional_metadata=invalid_metadata
            )
            assert success is True

        # The file should be created but validation should fail
        meta_validator = cdf.MetaSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/meta.json"
        )

        # Validation should fail due to type mismatches
        with pytest.raises(Exception):  # Could be ValidationError or similar
            meta_validator.validate_schema(sample=meta_path)

        # Clean up
        Path(meta_path).unlink()
        Path(tracking_path).unlink()

    def test_cdf_positions(self):
        """
        Make sure we have not introduced any non-cdf supported positions to kloppy PositionType.
        If we did, update map_position_type_code_to_cdf
        """

        test_list = []

        for position in PositionType:
            if is_valid_cdf_position_code(position.code):
                pass
            else:
                test_list.append(position.code)

        assert set(test_list) == set(
            [
                "UNK",
                "DEF",
                "FB",
                "LWB",
                "RWB",
                "MID",
                "DM",
                "AM",
                "WM",
                "ATT",
                "LF",
                "ST",
                "RF",
            ]
        )
