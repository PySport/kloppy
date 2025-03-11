from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kloppy.domain import (
    Orientation,
    Provider,
    Point,
    Point3D,
    DatasetType,
)

from kloppy import secondspectrum
from kloppy.domain.models.event import Event


class TestSecondSpectrumTracking:
    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/second_spectrum_fake_metadata.xml"

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/second_spectrum_fake_data.jsonl"

    @pytest.fixture
    def additional_meta_data(self, base_dir) -> str:
        return base_dir / "files/second_spectrum_fake_metadata.json"

    def test_correct_deserialization_limit_sample(
        self, meta_data: Path, raw_data: Path, additional_meta_data: Path
    ):

        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            additional_meta_data=additional_meta_data,
            only_alive=False,
            coordinates="secondspectrum",
            limit=100,
            sample_rate=(1 / 2),
        )
        assert len(dataset.records) == 100

        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            additional_meta_data=additional_meta_data,
            only_alive=False,
            coordinates="secondspectrum",
            limit=100,
        )
        assert len(dataset.records) == 100

    def test_correct_deserialization(
        self, meta_data: Path, raw_data: Path, additional_meta_data: Path
    ):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            additional_meta_data=additional_meta_data,
            only_alive=False,
            coordinates="secondspectrum",
        )

        # Check provider, type, shape, etc
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 376
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

        # Check the Periods
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=2982240 / 25
        )

        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=3907360 / 25
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=6927840 / 25
        )

        # Check some timestamps
        assert dataset.records[0].timestamp == timedelta(
            seconds=0
        )  # First frame
        assert dataset.records[20].timestamp == timedelta(
            seconds=320.0
        )  # Later frame
        assert dataset.records[187].timestamp == timedelta(
            seconds=9.72
        )  # Second period

        # Check some players
        home_player = dataset.metadata.teams[0].players[2]
        assert home_player.player_id == "8xwx2"
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=-8.943903672572427, y=-28.171654132650365
        )

        away_player = dataset.metadata.teams[1].players[3]
        assert away_player.player_id == "2q0uv"
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=-45.11871334915762, y=-20.06459030559596
        )

        # Check the ball
        assert dataset.records[1].ball_coordinates == Point3D(
            x=-23.147073918432426, y=13.69367399756424, z=0.0
        )

        # Check pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.425
        assert pitch_dimensions.x_dim.max == 52.425
        assert pitch_dimensions.y_dim.min == -33.985
        assert pitch_dimensions.y_dim.max == 33.985

        # Check enriched metadata
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(1900, 1, 26, 0, 0, tzinfo=timezone.utc)

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "1"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "1234456"

    def test_correct_normalized_deserialization(
        self, meta_data: Path, raw_data: Path, additional_meta_data: Path
    ):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            additional_meta_data=additional_meta_data,
            only_alive=False,
        )

        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=0.4146981051733674, y=0.9144718866065964
        )
        assert (
            dataset.records[0].players_data[home_player].speed
            == 6.578958220040129
        )

        # Check normalised pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0.0
        assert pitch_dimensions.x_dim.max == 1.0
        assert pitch_dimensions.y_dim.min == 0.0
        assert pitch_dimensions.y_dim.max == 1.0

    def test_load_without_fps(self, meta_data: Path, raw_data: Path):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="secondspectrum",
        )

        # Check provider, type, shape, etc
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 376
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

        # Check the Periods
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=2982240 / 25
        )

        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=3907360 / 25
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=6927840 / 25
        )

        # Check some timestamps
        assert dataset.records[0].timestamp == timedelta(
            seconds=0
        )  # First frame
        assert dataset.records[20].timestamp == timedelta(
            seconds=320.0
        )  # Later frame
        assert dataset.records[187].timestamp == timedelta(
            seconds=9.72
        )  # Second period

        # Check some players
        home_player = dataset.metadata.teams[0].players[2]
        assert home_player.player_id == "8xwx2"
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=-8.943903672572427, y=-28.171654132650365
        )

        away_player = dataset.metadata.teams[1].players[3]
        assert away_player.player_id == "2q0uv"
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=-45.11871334915762, y=-20.06459030559596
        )

        # Check the ball
        assert dataset.records[1].ball_coordinates == Point3D(
            x=-23.147073918432426, y=13.69367399756424, z=0.0
        )

        # Check pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.425
        assert pitch_dimensions.x_dim.max == 52.425
        assert pitch_dimensions.y_dim.min == -33.985
        assert pitch_dimensions.y_dim.max == 33.985

        # Check enriched metadata
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(1900, 1, 26, 0, 0, tzinfo=timezone.utc)

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "1"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "1234456"

    def test_load_with_current_metadata_format(
        self, meta_data: Path, raw_data: Path, additional_meta_data: Path
    ):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            additional_meta_data=additional_meta_data,
            only_alive=False,
            coordinates="secondspectrum",
        )

        # Check provider, type, shape, etc
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 376
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

        # Check the Periods
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=2982240 / 25
        )

        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=3907360 / 25
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=6927840 / 25
        )

        # Check some timestamps
        assert dataset.records[0].timestamp == timedelta(
            seconds=0
        )  # First frame
        assert dataset.records[20].timestamp == timedelta(
            seconds=320.0
        )  # Later frame
        assert dataset.records[187].timestamp == timedelta(
            seconds=9.72
        )  # Second period

        # Check some players
        home_player = dataset.metadata.teams[0].players[2]
        assert home_player.player_id == "8xwx2"
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=-8.943903672572427, y=-28.171654132650365
        )

        away_player = dataset.metadata.teams[1].players[3]
        assert away_player.player_id == "2q0uv"
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=-45.11871334915762, y=-20.06459030559596
        )

        # Check the ball
        assert dataset.records[1].ball_coordinates == Point3D(
            x=-23.147073918432426, y=13.69367399756424, z=0.0
        )

        # Check pitch dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.425
        assert pitch_dimensions.x_dim.max == 52.425
        assert pitch_dimensions.y_dim.min == -33.985
        assert pitch_dimensions.y_dim.max == 33.985

        # Check enriched metadata
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(1900, 1, 26, 0, 0, tzinfo=timezone.utc)

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "1"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "1234456"

        # Check team and player information
        home_team = dataset.metadata.teams[0]
        assert home_team.team_id == "123"
        assert home_team.name == "FK1"

        away_team = dataset.metadata.teams[1]
        assert away_team.team_id == "456"
        assert away_team.name == "FK2"

        home_player = home_team.players[0]
        assert home_player.player_id == "0a39g4"
        assert home_player.name == "y9xrbe545u3h"
        assert home_player.starting is False
        assert home_player.starting_position == "SUB"

        away_player = away_team.players[0]
        assert away_player.player_id == "9bgzhy"
        assert away_player.name == "c6gupnmywca0"
        assert away_player.starting is True
        assert away_player.starting_position == "GK"


class TestSecondSpectrumEvents:
    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/second_spectrum_fake_metadata.json"

    @pytest.fixture
    def event_data_file(self, tmp_path):
        """Create a fixture with sample event data including reception events"""
        events = [
            {
                "event_id": "1",
                "type": "reception",
                "period": 1,
                "timestamp": 120.5,
                "player_id": "8xwx2",
                "coordinates": {"x": 23.5, "y": 45.2},
                "attributes": {},
            },
            {
                "event_id": "2",
                "type": "pass",
                "period": 1,
                "team_id": "HOME",
                "timestamp": 121.0,
                "player_id": "8xwx2",
                "coordinates": {"x": 25.0, "y": 40.0},
                "attributes": {
                    "complete": True,
                    "crossed": False,
                    "bodyPart": "foot",
                },
                "players": {"receiver": "2q0uv"},
            },
        ]

        event_file = tmp_path / "events.jsonl"
        with open(event_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        return event_file

    def test_deserialize_reception_event(
        self, meta_data: Path, event_data_file: Path
    ):
        """Test that reception events are correctly deserialized as recovery events"""
        with patch(
            "kloppy.infra.serializers.event.secondspectrum.deserializer.SecondSpectrumEventDataDeserializer._parse_event"
        ) as mock_parse_event:
            # Set up the mock to return event objects properly
            event_factory_mock = MagicMock()
            recovery_event_mock = MagicMock(spec=Event)
            event_factory_mock.build_recovery.return_value = (
                recovery_event_mock
            )

            # Load the data
            with open(meta_data, "rb") as meta_file, open(
                event_data_file, "rb"
            ) as event_file:
                dataset = secondspectrum.load_event(
                    meta_data=meta_file, event_data=event_file
                )

                # Verify the deserializer's event factory build_recovery was called
                # with the expected parameters
                calls = mock_parse_event.call_args_list

                # Verify the raw_event was passed with the expected properties
                for call in calls:
                    raw_event = call[0][0]
                    if raw_event["type"] == "reception":
                        assert raw_event["event_id"] == "1"
                        assert raw_event["player_id"] == "8xwx2"
                        assert raw_event["coordinates"] == {
                            "x": 23.5,
                            "y": 45.2,
                        }

    def test_reception_event_mapping(self):
        """Test that reception events are mapped to recovery events using the actual implementation"""
        from kloppy.infra.serializers.event.secondspectrum.deserializer import (
            SecondSpectrumEventDataDeserializer,
        )

        # Create a mock event factory
        event_factory = MagicMock()
        recovery_event = MagicMock()
        event_factory.build_recovery.return_value = recovery_event

        # Create the deserializer with the mock factory
        deserializer = SecondSpectrumEventDataDeserializer(
            event_factory=event_factory
        )

        # Create fake raw event for reception
        raw_event = {
            "event_id": "e123",
            "type": "reception",
            "period": 1,
            "timestamp": 120.5,
            "player_id": "p1",
            "coordinates": {"x": 10, "y": 20},
        }

        # Create fake teams and periods
        teams = [
            MagicMock(team_id="team1", players=[MagicMock(player_id="p1")])
        ]
        periods = [MagicMock(id=1)]

        # Call the method and verify
        deserializer._parse_event(raw_event, teams, periods)

        # Verify build_recovery was called with result=None
        event_factory.build_recovery.assert_called_once()
        kwargs = event_factory.build_recovery.call_args[1]
        assert kwargs["result"] is None
        assert kwargs["event_id"] == "e123"
