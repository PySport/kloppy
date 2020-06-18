import os

from kloppy import OptaSerializer
from kloppy.domain import AttackingDirection, Period, Orientation


class TestOpta:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = OptaSerializer()

        with open(f"{base_dir}/files/opta_f24.xml", "rb") as f24_data, open(
            f"{base_dir}/files/opta_f7.xml", "rb"
        ) as f7_data:

            dataset = serializer.deserialize(
                inputs={"f24_data": f24_data, "f7_data": f7_data}
            )

        assert len(dataset.events) == 17
        assert len(dataset.periods) == 2
        assert dataset.orientation == Orientation.ACTION_EXECUTING_TEAM
        assert dataset.periods[0] == Period(
            id=1,
            start_timestamp=1537707733.608,
            end_timestamp=1537710501.222,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.periods[1] == Period(
            id=2,
            start_timestamp=1537711528.873,
            end_timestamp=1537714537.788,
            attacking_direction=AttackingDirection.NOT_SET,
        )
