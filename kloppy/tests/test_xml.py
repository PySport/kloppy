import os
from datetime import timedelta

from pandas import DataFrame
from pandas._testing import assert_frame_equal

from kloppy.domain import Period
from kloppy import sportscode
from kloppy.infra.serializers.code.sportscode import SportsCodeSerializer


class TestXMLCodeTracking:
    def test_correct_deserialization(self, base_dir):
        dataset = sportscode.load(base_dir / "files/code_xml.xml")

        assert len(dataset.metadata.periods) == 1

        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert (
            dataset.metadata.periods[0].end_timestamp
            == dataset.codes[-1].end_timestamp
        )

        assert len(dataset.codes) == 3
        assert dataset.codes[0].code_id == "P1"
        assert dataset.codes[0].code == "PASS"
        assert dataset.codes[0].timestamp == timedelta(seconds=3.6)
        assert dataset.codes[0].end_timestamp == timedelta(seconds=9.7)
        assert dataset.codes[0].labels == {
            "Team": "Henkie",
            "Packing.Value": 1,
            "Receiver": "Klaas Nøme",
        }

        dataframe = dataset.to_pandas()

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
                "Expected.Goal.Value": [None, None, 0.13],
            }
        )

        assert_frame_equal(dataframe, expected_data_frame)

    def test_correct_serialization(self, base_dir):
        dataset = sportscode.load(base_dir / "files/code_xml.xml")

        del dataset.codes[2:]

        # Make sure that data in Period 2 get the timestamp corrected
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

        serializer = SportsCodeSerializer()
        output = serializer.serialize(dataset)

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
        expected_output = bytes(expected_output, "utf-8")
        assert output == expected_output
