import tempfile
from pathlib import Path

import pytest
import cdf

from kloppy import sportec
from kloppy.domain import TrackingDataset
from kloppy.infra.serializers.tracking.cdf.serializer import (
    CDFTrackingDataSerializer,
    CDFOutputs,
)


class TestCDFSerializer:
    @pytest.fixture
    def raw_data(self, base_dir) -> Path:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/sportec_meta.xml"

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

    def test_produces_valid_cdf_output(self, dataset):
        """Test that CDFTrackingDataSerializer produces valid CDF output."""
        serializer = CDFTrackingDataSerializer()

        # Create temporary files with .jsonl extension for CDF validation
        with tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".json", delete=False
        ) as meta_file, tempfile.NamedTemporaryFile(
            mode="w+b", suffix=".jsonl", delete=False
        ) as tracking_file:

            outputs = CDFOutputs(
                meta_data=meta_file, tracking_data=tracking_file
            )

            # Serialize the small Sportec dataset to CDF format
            success = serializer.serialize(dataset, outputs)
            assert success is True

            # Close files to ensure data is written
            meta_file.close()
            tracking_file.close()

            # Validate using CDF validators

            # Validate meta data first.
            meta_validator = cdf.MetaSchemaValidator()
            meta_validator.validate_schema(sample=meta_file.name)

            # Validate tracking data
            tracking_validator = cdf.TrackingSchemaValidator()
            tracking_validator.validate_schema(sample=tracking_file.name)

            # Clean up temp files
            Path(meta_file.name).unlink()
            Path(tracking_file.name).unlink()
