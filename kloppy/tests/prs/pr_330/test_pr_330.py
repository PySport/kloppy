from datetime import datetime, timezone

from kloppy import statsperform, wyscout
from kloppy.domain import EventType, FormationType


class TestPR330:
    def test_9_player_formation_change(self, base_dir):
        dataset = wyscout.load(
            event_data=base_dir / "prs/pr_330/wyscout_events_v3.json",
            coordinates="wyscout",
        )

        assert len(dataset.find_all("formation_change")) == 1
        formation_change_event = dataset.get_event_by_id(
            "synthetic-3164-1927028854"
        )
        assert formation_change_event.event_type == EventType.FORMATION_CHANGE
        assert formation_change_event.formation_type == FormationType.UNKNOWN
