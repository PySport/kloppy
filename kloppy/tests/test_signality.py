from datetime import timedelta, datetime
from pathlib import Path

import pytest

from kloppy.domain import (
    Provider,
    Orientation,
    Point,
    Point3D,
    DatasetType,
    Ground,
)

from kloppy import signality


class TestSignalityTracking:
    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/signality_meta_data.json"

    @pytest.fixture
    def venue_information(self, base_dir) -> Path:
        return base_dir / "files/signality_venue_information.json"

    @pytest.fixture
    def p1_raw_data(self, base_dir) -> Path:
        return base_dir / "files/signality_p1_raw_data_subset.json"

    @pytest.fixture
    def p2_raw_data(self, base_dir) -> Path:
        return base_dir / "files/signality_p2_raw_data_subset.json"

    def test_correct_deserialization(
        self,
        p1_raw_data: Path,
        p2_raw_data: Path,
        meta_data: Path,
        venue_information: Path,
    ):
        dataset = signality.load(
            meta_data=meta_data,
            p1_raw_data=p1_raw_data,
            p2_raw_data=p2_raw_data,
            venue_information=venue_information,
            coordinates="signality",
        )

        assert dataset.metadata.provider == Provider.SIGNALITY
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 10
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == datetime(
            2024, 10, 6, 12, 0, 1, 408000
        )
        assert dataset.metadata.periods[0].end_timestamp == datetime(
            2024, 10, 6, 12, 48, 43, 858000
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == datetime(
            2024, 10, 6, 13, 4, 45, 775000
        )
        assert dataset.metadata.periods[1].end_timestamp == datetime(
            2024, 10, 6, 13, 54, 11, 730000
        )

        start_frame = dataset.records[0]
        assert start_frame.frame_id == 0
        assert start_frame.timestamp == timedelta(milliseconds=12)

        end_frame = dataset.records[-1]
        assert end_frame.frame_id == 147211
        assert end_frame.timestamp == timedelta(seconds=2965, milliseconds=955)

        home_team = dataset.metadata.teams[0]
        assert home_team.ground == Ground.HOME
        assert len(home_team.players) == 20

        home_team_gk = home_team.get_player_by_id(45)
        start_frame_home_team_gk_data = start_frame.players_data[home_team_gk]
        assert start_frame_home_team_gk_data.coordinates == Point(
            x=-47.78, y=0.59
        )
        assert start_frame_home_team_gk_data.speed == 0.65

        away_team = dataset.metadata.teams[1]
        assert away_team.ground == Ground.AWAY
        assert len(away_team.players) == 20

        away_team_gk = away_team.get_player_by_id(1)
        start_frame_away_team_gk_data = start_frame.players_data[away_team_gk]
        assert start_frame_away_team_gk_data.coordinates == Point(
            x=46.48, y=0.23
        )
        assert start_frame_away_team_gk_data.speed == 0.942

        assert start_frame.ball_coordinates == Point3D(x=-41.18, y=0.08, z=0)

        first_second_half_frame = next(
            frame for frame in dataset.frames if frame.period.id == 2
        )
        assert first_second_half_frame.frame_id == 73063

        first_second_half_frame_home_team_gk_data = (
            first_second_half_frame.players_data[home_team_gk]
        )
        assert first_second_half_frame_home_team_gk_data.coordinates == Point(
            x=45.37, y=0.22
        )

        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -104.82 / 2
        assert pitch_dimensions.x_dim.max == 104.82 / 2
        assert pitch_dimensions.y_dim.min == -68.407 / 2
        assert pitch_dimensions.y_dim.max == 68.407 / 2
