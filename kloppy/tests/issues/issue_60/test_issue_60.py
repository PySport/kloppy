from kloppy import opta
import os


class TestIssue60:
    def test_deleted_event_opta(self):
        dir_path = os.path.dirname(__file__)
        deleted_event_id = "2087733359"

        event_dataset = opta.load(
            f7_data=os.path.join(dir_path, "opta_f7.xml"),
            f24_data=os.path.join(dir_path, "opta_f24.xml"),
        )
        df = event_dataset.to_df()

        assert deleted_event_id not in df["event_id"].to_list()

        # OPTA F24 file: Pass -> Deleted Event -> Tackle
        assert event_dataset.events[16].event_name == "pass"
        assert (
            event_dataset.events[17].event_name == "duel"
        )  # Deleted Event is filter out
