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
            limit=10,  # only ten frames even if we are just gona use one of them.
            sample_rate=None,
        )

        return dataset

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

            # Validate tracking data
            tracking_validator = cdf.TrackingSchemaValidator(schema="cdf/files/schema/tracking_v0.2.0.json")
            tracking_validator.validate_schema(sample=tracking_file.name)

            # Validate meta data first.
            meta_validator = cdf.MetaSchemaValidator(schema="cdf/files/schema/meta_v0.2.0.json")
            meta_validator.validate_schema(sample=meta_file.name)

            
            # Clean up temp files
            Path(meta_file.name).unlink()
            Path(tracking_file.name).unlink()
