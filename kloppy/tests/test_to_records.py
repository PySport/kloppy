from pathlib import Path

import pytest
from kloppy import statsbomb

from kloppy.domain import EventDataset, Point
from kloppy.domain.services.transformers.attribute import (
    DistanceToGoalTransformer,
    DistanceToOwnGoalTransformer,
)


class TestToRecords:
    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/statsbomb_event.json"

    @pytest.fixture
    def lineup_data(self, base_dir) -> str:
        return base_dir / "files/statsbomb_lineup.json"

    @pytest.fixture
    def dataset(self, event_data: Path, lineup_data: Path) -> EventDataset:
        return statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            coordinates="statsbomb",
        )

    def test_default_columns(self, dataset: EventDataset):
        records = dataset.to_records()
        assert len(records) == 4039
        assert list(records[0].keys()) == [
            "event_id",
            "event_type",
            "result",
            "success",
            "period_id",
            "timestamp",
            "end_timestamp",
            "ball_state",
            "ball_owning_team",
            "team_id",
            "player_id",
            "coordinates_x",
            "coordinates_y",
        ]

    def test_string_columns(self, dataset: EventDataset):
        """
        When string columns passed to to_records the data must be searched from:
        1. the output of Default()
        2. attributes of the event
        """

        records = dataset.filter("pass").to_records(
            "timestamp", "coordinates_x", "coordinates"
        )
        assert records[0] == {
            "timestamp": 0.098,
            "coordinates_x": 60.5,
            "coordinates": Point(x=60.5, y=40.5),
        }

    def test_string_wildcard_columns(self, dataset: EventDataset):
        """
        Make sure it's possible to specify wildcard pattern to match attributes.
        """

        records = dataset.filter("pass").to_records(
            "timestamp",
            "player_id",
            "coordinates_*",
            DistanceToGoalTransformer(),
            DistanceToOwnGoalTransformer(),
        )
        assert records[0] == {
            "timestamp": 0.098,
            "player_id": "6581",
            "coordinates_x": 60.5,
            "coordinates_y": 40.5,
            "distance_to_goal": 59.50210080324896,
            "distance_to_own_goal": 60.502066080424065,
        }
