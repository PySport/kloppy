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
        # return sportec.load_tracking(
        #     raw_data=raw_data,
        #     meta_data=meta_data,
        #     coordinates="sportec",
        #     limit=None,
        #     only_alive=False,
        # )
    
        from kloppy import pff

        # Path to data
        roster_path = "/home/student/Documents/AIMS/Intership/pysport/pysport-aims/first_week/data/3812/3812_roster.json"
        metadata_path = "/home/student/Documents/AIMS/Intership/pysport/pysport-aims/first_week/data/3812/3812_metadata.json"
        raw_data_path = "/home/student/Documents/AIMS/Intership/pysport/pysport-aims/first_week/data/3812/3812.jsonl.bz2"

        # Loading
        dataset = pff.load_tracking(
            raw_data=raw_data_path,
            meta_data=metadata_path,
            roster_meta_data=roster_path,
            coordinates="pff",
            limit=30000,  # only ten frames even if we are just gona use one of them.
            sample_rate=None,
        )

        return dataset

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