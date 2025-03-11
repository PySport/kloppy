import json
from pathlib import Path
import pytest
from kloppy import secondspectrum
from kloppy.domain import Provider, DatasetType


class TestSecondSpectrumTracking:
    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/secondspectrum_fake_metadata.json"

    @pytest.fixture
    def raw_data(self, base_dir) -> Path:
        return base_dir / "files/second_spectrum_fake_data.jsonl"

    @pytest.fixture
    def additional_meta_data(self, base_dir) -> Path:
        return base_dir / "files/second_spectrum_fake_metadata.json"

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

        assert dataset.metadata.provider == Provider.SECONDSPECTRUM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) > 0
        assert len(dataset.metadata.periods) > 0

        players = [p for team in dataset.metadata.teams for p in team.players]
        player = players[0]
        assert player is not None
        assert dataset.records[0].players_coordinates[player] is not None
        assert dataset.records[0].ball_coordinates is not None

        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min is not None
        assert pitch_dimensions.x_dim.max is not None

    def test_correct_normalized_deserialization(
        self, meta_data: Path, raw_data: Path, additional_meta_data: Path
    ):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            additional_meta_data=additional_meta_data,
            only_alive=False,
        )

        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0.0
        assert pitch_dimensions.x_dim.max == 1.0
        assert pitch_dimensions.y_dim.min == 0.0
        assert pitch_dimensions.y_dim.max == 1.0

        players = [p for team in dataset.metadata.teams for p in team.players]
        player = players[0]
        assert dataset.records[0].players_coordinates[player] is not None
        assert dataset.records[0].players_data[player].speed is not None

    def test_load_without_fps(self, meta_data: Path, raw_data: Path):
        dataset = secondspectrum.load(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="secondspectrum",
        )

        assert dataset.metadata.provider == Provider.SECONDSPECTRUM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) > 0

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

        assert dataset.metadata.provider == Provider.SECONDSPECTRUM
        assert dataset.dataset_type == DatasetType.TRACKING
        assert dataset.metadata.teams[0] is not None
        assert dataset.metadata.teams[1] is not None
