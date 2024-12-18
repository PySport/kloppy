import pytest

from kloppy import wyscout
from kloppy.exceptions import DeserializationWarning


def test_ignore_unknown_player(base_dir):
    with pytest.warns(
        DeserializationWarning,
        match="the player does not appear to be part of that team's lineup",
    ):
        dataset = wyscout.load(
            event_data=base_dir / "prs" / "pr_358" / "wyscout_events_v3.json",
            coordinates="wyscout",
        )

        assert len(dataset.events) == 2

        assert dataset.events[1].player is None
