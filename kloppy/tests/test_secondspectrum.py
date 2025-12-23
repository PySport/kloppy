from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy import secondspectrum
from kloppy.domain import (
    DatasetType,
    Orientation,
    Point,
    Point3D,
    Provider,
)


class TestSecondSpectrumTracking:
    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/second_spectrum_fake_metadata.xml"

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/second_spectrum_fake_data.jsonl"

    @pytest.fixture
    def raw_data_utf8sig(self, base_dir) -> str:
        return base_dir / "files/second_spectrum_fake_data_utf8sig.jsonl"

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

    def test_correct_deserialization_ascii(
        self,
        meta_data: Path,
        raw_data_utf8sig: Path,
        additional_meta_data: Path,
    ):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data_utf8sig,
            additional_meta_data=additional_meta_data,
            only_alive=False,
            coordinates="secondspectrum",
        )

        assert len(dataset.records) == 13

    def test_utf8_fails_with_bom_but_utf8sig_works(self, raw_data_utf8sig):
        import json

        with open(raw_data_utf8sig, "rb") as f:
            first_line = f.readline().strip()
            decoded_utf8 = first_line.decode("utf-8")

            with pytest.raises(
                json.JSONDecodeError, match="Unexpected UTF-8 BOM"
            ):
                json.loads(decoded_utf8)

            with pytest.raises(UnicodeDecodeError):
                first_line.decode("ascii")

        with open(raw_data_utf8sig, "rb") as f:
            first_line = f.readline().strip()
            decoded_utf8sig = first_line.decode("utf-8-sig")

            data = json.loads(decoded_utf8sig)
            assert isinstance(data, dict)
