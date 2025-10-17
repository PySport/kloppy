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

        # Instantiate Validators
        meta_validator = cdf.MetaSchemaValidator(schema="cdf/files/v0.2.1/schema/meta.json")
        tracking_validator = cdf.TrackingSchemaValidator(schema="cdf/files/v0.2.1/schema/tracking.json")

        with tempfile.NamedTemporaryFile(mode="w+b", suffix=".json", delete=False) as meta_file:
            # Initialize empty list for tracking files
            tracking_files: list[tempfile._TemporaryFileWrapper] = []
            # Instantiate the named tuple for outputs
            outputs = CDFOutputs(
                meta_data=meta_file,
                tracking_data=tracking_files
            )
            # Serialize the dataset
            success = serializer.serialize(dataset, outputs)
            assert success is True
            # Save paths for validation after leaving the block
            meta_path = meta_file.name
            tracking_paths = [f.name for f in outputs.tracking_data]

        # Validate metadata
        meta_validator.validate_schema(sample=meta_path)
        # Validate all tracking frame files
        for path in tracking_paths:
            tracking_validator.validate_schema(sample=path)

        Path(meta_path).unlink()
        for path in tracking_paths:
            Path(path).unlink()