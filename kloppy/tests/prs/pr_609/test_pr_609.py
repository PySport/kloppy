from kloppy import wyscout
from kloppy.domain import EventType, SetPieceType


def test_extra_time_period_parsing(base_dir):
    """Test that extra-time period codes ("E1", "E2") are parsed correctly.

    Regression test for issue #609 — 10 matches failed due to E1/E2 crashing int().
    Real failing match: 1694426.
    """
    dataset = wyscout.load(
        event_data=base_dir
        / "prs"
        / "pr_609"
        / "wyscout_events_v2_extra_time.json",
        coordinates="wyscout",
        data_version="V2",
    )

    assert len(dataset.events) == 2
    assert len(dataset.metadata.periods) == 2

    period_ids = [p.id for p in dataset.metadata.periods]
    assert 3 in period_ids
    assert dataset.metadata.periods[1].id == 3


def test_shot_as_last_event(base_dir):
    """Test that a shot event as the last event in a match doesn't crash.

    Regression test for issue #609 — 6 matches failed when _parse_shot tried to
    access next_event without checking if it was None.
    Real failing matches: 1694433, 2516925.
    """
    dataset = wyscout.load(
        event_data=base_dir
        / "prs"
        / "pr_609"
        / "wyscout_events_v2_shot_last_event.json",
        coordinates="wyscout",
        data_version="V2",
    )

    assert len(dataset.events) == 1
    last_event = dataset.events[0]
    assert last_event.event_type == EventType.SHOT


def test_freekick_shot_as_last_event(base_dir):
    """Test that a free-kick shot as the last event doesn't crash.

    Verifies the fix for _parse_shot covers the _parse_set_piece call path.
    Real failing match reference: 2516925.
    """
    dataset = wyscout.load(
        event_data=base_dir
        / "prs"
        / "pr_609"
        / "wyscout_events_v2_freekick_shot_last_event.json",
        coordinates="wyscout",
        data_version="V2",
    )

    assert len(dataset.events) == 1
    shot_event = dataset.events[0]
    assert shot_event.event_type == EventType.SHOT

    set_piece_qualifiers = [
        q
        for q in shot_event.qualifiers
        if hasattr(q, "value") and isinstance(q.value, SetPieceType)
    ]
    assert len(set_piece_qualifiers) == 1
    assert set_piece_qualifiers[0].value == SetPieceType.FREE_KICK


def test_null_roster_entries_skipped(base_dir):
    """Test that null entries in a team's roster are silently skipped.

    Regression test for issue #609 — 22 matches failed when some teams had
    null entries in their players array (upstream data issue).
    Real failing match: 2499738.
    """
    dataset = wyscout.load(
        event_data=base_dir
        / "prs"
        / "pr_609"
        / "wyscout_events_v2_null_roster.json",
        coordinates="wyscout",
        data_version="V2",
    )

    home_team = dataset.metadata.teams[0]
    assert len(home_team.players) == 1
    assert home_team.players[0].player_id == "100"
    assert home_team.players[0].first_name == "Real"
