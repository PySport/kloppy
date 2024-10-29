from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    Point,
    EventDataset,
    SetPieceType,
    SetPieceQualifier,
    DatasetType,
    DuelQualifier,
    DuelType,
    EventType,
    GoalkeeperQualifier,
    GoalkeeperActionType,
    CardQualifier,
    CardType,
    Orientation,
    PassResult,
    FormationType,
    Time,
    PassType,
    PassQualifier,
)

from kloppy import wyscout


def test_ignore_unknown_player(base_dir):
    dataset = wyscout.load(
        event_data=base_dir / "prs" / "pr_358" / "wyscout_events_v3.json",
        coordinates="wyscout",
    )

    assert len(dataset.events) == 2

    assert dataset.events[1].player is None
