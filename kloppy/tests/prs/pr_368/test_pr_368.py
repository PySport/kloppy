from datetime import timedelta

import pytest

from kloppy import wyscout
from kloppy.domain import Time
from kloppy.exceptions import DeserializationWarning


def test_missing_second_timestamp_sub(base_dir):
    dataset = wyscout.load(
        event_data=base_dir / "prs" / "pr_368" / "wyscout_events_v3.json",
        coordinates="wyscout",
    )

    second_period = dataset.metadata.periods[1]

    sub_event_minute_timestamp = dataset.get_event_by_id(
        "substitution-489124-20395"
    )
    assert sub_event_minute_timestamp.time == Time(
        period=second_period, timestamp=timedelta(seconds=22 * 60)
    )

    sub_event_second_timestamp = dataset.get_event_by_id(
        "substitution-415809-703"
    )
    assert sub_event_second_timestamp.time == Time(
        period=second_period, timestamp=timedelta(seconds=4)
    )
