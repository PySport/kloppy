import pytest

from kloppy import wyscout
from kloppy.domain import EventType, ShotResult
from kloppy.exceptions import DeserializationWarning


def test_recognition_of_own_goal(base_dir):
    dataset = wyscout.load(
        event_data=base_dir / "prs" / "pr_393" / "wyscout_events_v3.json",
        coordinates="wyscout",
    )

    assert len(dataset.events) == 2

    own_goal = dataset.events[1]
    assert own_goal.event_type == EventType.SHOT
    assert own_goal.result == ShotResult.OWN_GOAL
