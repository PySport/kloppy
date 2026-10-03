from datetime import timedelta
from io import BytesIO

from pandas import DataFrame
from pandas._testing import assert_frame_equal
import pytest

from kloppy import sportscode
from kloppy.domain import Period
from kloppy.infra.serializers.code.sportscode import (
    SportsCodeOutputs,
    SportsCodeSerializer,
)


class TestXMLCodeTracking:
    """Tests for reading and writing SportsCode XML format."""

    @pytest.fixture
    def dataset(self, base_dir):
        """Load a sample SportsCode XML dataset."""
        return sportscode.load(base_dir / "files/code_xml.xml")

    def test_correct_deserialization(self, dataset, tmp_path):
        """
        Test if a SportsCode XML file is correctly deserialized.
        """
        # Verify metadata
        assert len(dataset.metadata.periods) == 1
        p1 = dataset.metadata.periods[0]

        assert p1.start_timestamp == timedelta(seconds=0)
        assert p1.end_timestamp == dataset.codes[-1].end_timestamp

        # Check that all codes were successfully loaded
        assert len(dataset.codes) == 3

        # Ensure codes are correctly parsed, including multi-value labels
        assert dataset.codes[0].code_id == "P1"
        assert dataset.codes[0].code == "PASS"
        assert dataset.codes[0].timestamp == timedelta(seconds=3.6)
        assert dataset.codes[0].end_timestamp == timedelta(seconds=9.7)
        assert dataset.codes[0].labels == {
            "Team": "Henkie",
            "Packing.Value": 1,
            "Receiver": "Klaas Nøme",
            "Qualifiers": ["Long ball", "Completed"],
        }

        # Verify to_df()
        dataframe = dataset.to_df(engine="pandas")
        expected_data_frame = DataFrame.from_dict(
            {
                "code_id": ["P1", "P2", "P3"],
                "period_id": [1, 1, 1],
                "timestamp": [
                    timedelta(seconds=3.6),
                    timedelta(seconds=68.3),
                    timedelta(seconds=103.6),
                ],
                "end_timestamp": [
                    timedelta(seconds=9.7),
                    timedelta(seconds=74.5),
                    timedelta(seconds=109.6),
                ],
                "code": ["PASS", "PASS", "SHOT"],
                "Team": ["Henkie", "Henkie", "Henkie"],
                "Packing.Value": [1, 3, None],
                "Receiver": ["Klaas Nøme", "Piet", None],
                "Qualifiers": [["Long ball", "Completed"], None, None],
                "Expected.Goal.Value": [None, None, 0.13],
            }
        )

        assert_frame_equal(dataframe, expected_data_frame)

        # Test round-trip serialization/deserialization preserves multi-value labels
        output_file = tmp_path / "codes.xml"
        sportscode.save(dataset, str(output_file))
        reloaded_dataset = sportscode.load(output_file)
        assert reloaded_dataset.codes[0].labels == dataset.codes[0].labels

    def test_correct_serialization(self, dataset):
        """
        Test if a CodeDataset is correctly serialized to SportsCode XML.
        """
        # Remove the third code to simplify testing multi-period timestamp logic
        # leaving one code for Period 1 and one code for Period 2.
        del dataset.codes[2:]

        # Explicitly assign P2 to a second period to verify that the serializer
        # correctly adds the period's temporal offset (45 minutes) to the code's timestamp.
        dataset.metadata.periods = [
            Period(
                id=1,
                start_timestamp=timedelta(seconds=0),
                end_timestamp=timedelta(minutes=45),
            ),
            Period(
                id=2,
                start_timestamp=timedelta(minutes=45, seconds=10),
                end_timestamp=timedelta(minutes=90),
            ),
        ]
        dataset.codes[1].period = dataset.metadata.periods[1]

        # Serialize the modified dataset into a memory buffer
        serializer = SportsCodeSerializer()
        with BytesIO() as buffer:
            serializer.serialize(dataset, SportsCodeOutputs(data=buffer))
            buffer.seek(0)
            output = buffer.read()

        expected_output = """<?xml version='1.0' encoding='utf-8'?>
<file>
  <ALL_INSTANCES>
    <instance>
      <ID>P1</ID>
      <start>3.6</start>
      <end>9.7</end>
      <code>PASS</code>
      <label>
        <group>Team</group>
        <text>Henkie</text>
      </label>
      <label>
        <group>Packing.Value</group>
        <text>1</text>
      </label>
      <label>
        <group>Receiver</group>
        <text>Klaas Nøme</text>
      </label>
      <label>
        <group>Qualifiers</group>
        <text>Long ball</text>
      </label>
      <label>
        <group>Qualifiers</group>
        <text>Completed</text>
      </label>
    </instance>
    <instance>
      <ID>P2</ID>
      <start>2768.3</start>
      <end>2774.5</end>
      <code>PASS</code>
      <label>
        <group>Team</group>
        <text>Henkie</text>
      </label>
      <label>
        <group>Packing.Value</group>
        <text>3</text>
      </label>
      <label>
        <group>Receiver</group>
        <text>Piet</text>
      </label>
    </instance>
  </ALL_INSTANCES>
</file>
"""
        # Verify the generated XML matches the expected string exactly.
        expected_output = bytes(expected_output, "utf-8")
        assert output == expected_output
        output_str = output.decode("utf-8")

        # Should have 2 Team labels (1 for P1, 1 for P2)
        assert output_str.count("<group>Team</group>") == 2
        assert "<text>Henkie</text>" in output_str

        # Should have 2 Qualifiers labels
        assert output_str.count("<group>Qualifiers</group>") == 2
        assert "<text>Long ball</text>" in output_str
        assert "<text>Completed</text>" in output_str
