from datetime import datetime, timezone

from kloppy import statsperform


class TestPR355:
    def test_abandoned_match_end_timestamp(self, base_dir):
        tracking_dataset = statsperform.load_tracking(
            ma1_data=base_dir / "prs/pr_355/statsperform_tracking_ma1.json",
            ma25_data=base_dir / "files/statsperform_tracking_ma25.txt",
            tracking_system="sportvu",
        )

        assert tracking_dataset.metadata.periods[-1].end_timestamp == datetime(
            2020, 8, 23, 12, 45, 22, tzinfo=timezone.utc
        )
