import tempfile
from pathlib import Path

import pytest

from kloppy import sportec, skillcorner
from kloppy.domain import TrackingDataset, PositionType
from kloppy.infra.serializers.tracking.cdf.serializer import (
    CDFTrackingDataSerializer,
    CDFOutputs,
)
from kloppy.infra.serializers.tracking.cdf.helpers import (
    is_valid_cdf_position_code,
)


def mimimum_valid_cdf_output(
    dataset, meta_data_validator, tracking_data_validator, tmp_path
):
    """Test that CDFTrackingDataSerializer produces valid CDF output."""
    meta_path = tmp_path / "metadata.json"
    tracking_path = tmp_path / "tracking.jsonl"

    with pytest.warns(
        UserWarning,
    ):
        dataset.to_cdf(
            metadata_output_file=str(meta_path),
            tracking_output_file=str(tracking_path),
            additional_metadata={},
        )

    dataset.to_cdf(
        metadata_output_file=str(meta_path),
        tracking_output_file=str(tracking_path),
        additional_metadata={
            "competition": dict(
                id="61",
            ),
            "season": dict(
                id="95",
            ),
            "stadium": dict(
                id="2914",
            ),
            "meta": dict(
                tracking=dict(version="v3", collection_timing="post_match")
            ),
        },
    )

    meta_data_validator.validate_schema(sample=meta_path)
    tracking_data_validator.validate_schema(sample=tracking_path, limit=None)


def produces_valid_cdf_output_with_additional_metadata(
    dataset, meta_data_validator, tracking_data_validator, tmp_path
):
    """Test that CDFTrackingDataSerializer produces valid CDF output with additional metadata."""

    from cdf.domain import (
        CdfMetaDataSchema,
        Stadium,
        Competition,
        Season,
        Meta,
        Tracking,
    )

    # Define additional metadata
    additional_meta_data = CdfMetaDataSchema(
        competition=Competition(
            id="61", name="A-League", type="mens", format="league"
        ),
        season=Season(id="95", name="2024/2025"),
        stadium=Stadium(
            id="2914",
            name="Kayo Stadium",
        ),
        meta=Meta(
            tracking=Tracking(
                version="v3",
                collection_timing="post_match",
            )
        ),
    )

    meta_path = tmp_path / "metadata.json"
    tracking_path = tmp_path / "tracking.jsonl"

    dataset.to_cdf(
        metadata_output_file=str(meta_path),
        tracking_output_file=str(tracking_path),
        additional_metadata=additional_meta_data,
    )

    meta_data_validator.validate_schema(sample=meta_path)
    tracking_data_validator.validate_schema(sample=tracking_path, limit=None)


def serializer_handles_invalid_metadata_types(dataset):
    """Test that CDFTrackingDataSerializer handles invalid metadata types gracefully."""
    import cdf

    serializer = CDFTrackingDataSerializer()

    with tempfile.NamedTemporaryFile(
        mode="w+b", suffix=".json", delete=False
    ) as meta_file, tempfile.NamedTemporaryFile(
        mode="w+b", suffix=".jsonl", delete=False
    ) as tracking_file:

        meta_path = meta_file.name
        tracking_path = tracking_file.name

        outputs = CDFOutputs(meta_data=meta_file, tracking_data=tracking_file)

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
                    "version": 1.0,  # Should be string,
                    "collection_timing": "Nothing",
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


class TestCDFSerializer:
    @pytest.fixture
    def raw_data(self, base_dir) -> Path:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/sportec_meta.xml"

    @pytest.fixture
    def meta_data_v3(self, base_dir) -> str:
        return base_dir / "files/skillcorner_v3_meta_data-2.json"

    @pytest.fixture
    def raw_data_v3(self, base_dir) -> str:
        return base_dir / "files/skillcorner_v3_raw_data-2.jsonl"

    @pytest.fixture
    def dataset_sportec(
        self, raw_data: Path, meta_data: Path
    ) -> TrackingDataset:
        """Load a small Sportec tracking data snippet for testing CDF serialization."""
        return sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            limit=None,
            only_alive=False,
        )

    @pytest.fixture
    def dataset_skillcorner(self, raw_data_v3: Path, meta_data_v3: Path):
        return skillcorner.load(
            meta_data=meta_data_v3,
            raw_data=raw_data_v3,
            coordinates="skillcorner",
            include_empty_frames=True,
            only_alive=False,
        )

    @pytest.fixture
    def meta_data_validator(self):
        import cdf

        # Instantiate Validators
        return cdf.MetaSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/meta.json"
        )

    @pytest.fixture
    def tracking_data_validator(self):
        import cdf

        # Instantiate Validators
        return cdf.TrackingSchemaValidator(
            schema=f"cdf/files/v{cdf.VERSION}/schema/tracking.json"
        )

    def test_produces_valid_cdf_output(
        self,
        dataset_sportec,
        dataset_skillcorner,
        tracking_data_validator,
        meta_data_validator,
        tmp_path,
    ):
        mimimum_valid_cdf_output(
            dataset_sportec,
            meta_data_validator,
            tracking_data_validator,
            tmp_path,
        )
        mimimum_valid_cdf_output(
            dataset_skillcorner,
            meta_data_validator,
            tracking_data_validator,
            tmp_path,
        )

    def test_produces_valid_cdf_output_with_additional_metadata(
        self,
        dataset_skillcorner,
        dataset_sportec,
        tracking_data_validator,
        meta_data_validator,
        tmp_path,
    ):
        produces_valid_cdf_output_with_additional_metadata(
            dataset_skillcorner,
            meta_data_validator,
            tracking_data_validator,
            tmp_path,
        )
        produces_valid_cdf_output_with_additional_metadata(
            dataset_sportec,
            meta_data_validator,
            tracking_data_validator,
            tmp_path,
        )

    def test_serializer_handles_invalid_metadata_types(
        self, dataset_skillcorner, dataset_sportec
    ):
        serializer_handles_invalid_metadata_types(dataset=dataset_skillcorner)
        serializer_handles_invalid_metadata_types(dataset=dataset_sportec)

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
