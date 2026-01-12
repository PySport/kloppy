from pathlib import Path

import pytest

from kloppy import cdf
from kloppy.domain import (
    BallState,
    DatasetType,
    Ground,
    Orientation,
    Point3D,
    Provider,
)


class TestCDFDeserializer:
    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/cdf_metadata.json"

    @pytest.fixture
    def raw_data(self, base_dir) -> Path:
        return base_dir / "files/cdf_tracking.jsonl"

    def test_correct_deserialization(
        self, meta_data: Path, raw_data: Path
    ) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        assert dataset.dataset_type == DatasetType.TRACKING
        assert dataset.metadata.provider == Provider.CDF

        assert dataset.metadata.frame_rate == 10

        assert len(dataset.metadata.teams) == 2
        home_team = dataset.metadata.teams[0]
        away_team = dataset.metadata.teams[1]

        assert home_team.ground == Ground.HOME
        assert home_team.name == "Brisbane Roar FC"
        assert home_team.team_id == "1802"

        assert away_team.ground == Ground.AWAY
        assert away_team.name == "Perth Glory Football Club"
        assert away_team.team_id == "871"

        assert len(home_team.players) == 18
        assert len(away_team.players) == 18

        # Check periods
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[1].id == 2

        assert len(dataset.records) == 101

        first_frame = dataset.records[0]
        assert first_frame.frame_id == 0
        assert first_frame.period.id == 1

        assert first_frame.ball_coordinates is not None
        assert isinstance(first_frame.ball_coordinates, Point3D)
        assert first_frame.ball_coordinates.x == pytest.approx(0.66, abs=0.01)
        assert first_frame.ball_coordinates.y == pytest.approx(-0.58, abs=0.01)
        assert first_frame.ball_coordinates.z == pytest.approx(0.29, abs=0.01)

        assert first_frame.ball_state == BallState.DEAD

    def test_correct_normalized_deserialization(
        self, meta_data: Path, raw_data: Path
    ) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            # No coordinates specified = normalized
        )

        first_frame = dataset.records[0]
        # First home player in metadata is player_id "51050"
        home_player = dataset.metadata.teams[0].players[0]
        assert home_player.player_id == "51050"

        coords = first_frame.players_coordinates[home_player]
        # Raw CDF coords: x=-14.92, y=0.45
        # Normalized coordinates (kloppy transforms to 0-1 range)
        assert coords.x == pytest.approx(0.358, abs=0.001)
        assert coords.y == pytest.approx(0.493, abs=0.001)

    def test_limit(self, meta_data: Path, raw_data: Path) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            limit=50,
            coordinates="cdf",
        )

        assert len(dataset.records) == 50

    def test_sample_rate(self, meta_data: Path, raw_data: Path) -> None:
        dataset_all = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        dataset_sampled = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            sample_rate=0.5,
            coordinates="cdf",
        )

        assert len(dataset_all.records) == 101
        assert len(dataset_sampled.records) == 51

    def test_only_alive(self, meta_data: Path, raw_data: Path) -> None:
        dataset_all = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        dataset_alive = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=True,
            coordinates="cdf",
        )

        assert len(dataset_all.records) == 101
        assert len(dataset_alive.records) == 48

        for frame in dataset_alive.records:
            assert frame.ball_state == BallState.ALIVE

    def test_ball_coordinates_3d(self, meta_data: Path, raw_data: Path) -> None:
        """Test that 3D ball coordinates are correctly parsed."""
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        first_frame = dataset.records[0]
        assert first_frame.ball_coordinates is not None
        assert isinstance(first_frame.ball_coordinates, Point3D)
        assert hasattr(first_frame.ball_coordinates, "z")

    def test_player_coordinates(self, meta_data: Path, raw_data: Path) -> None:
        """Test that player coordinates are correctly parsed."""
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        first_frame = dataset.records[0]

        home_team = dataset.metadata.teams[0]
        away_team = dataset.metadata.teams[1]

        # First frame has 11 home + 11 away = 22 players
        assert len(first_frame.players_data) == 22

        for player in first_frame.players_data.keys():
            assert player.team in [home_team, away_team]

    def test_periods(self, meta_data: Path, raw_data: Path) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        assert len(dataset.metadata.periods) == 2

        period_1 = dataset.metadata.periods[0]
        period_2 = dataset.metadata.periods[1]

        assert period_1.id == 1
        assert period_2.id == 2

        first_half_frames = [f for f in dataset.records if f.period.id == 1]
        second_half_frames = [f for f in dataset.records if f.period.id == 2]

        assert len(first_half_frames) == 50
        assert len(second_half_frames) == 51

    def test_game_metadata(self, meta_data: Path, raw_data: Path) -> None:
        """Test that game metadata is correctly parsed."""
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        assert dataset.metadata.game_id == "1925299"

        assert dataset.metadata.date is not None
        assert dataset.metadata.date.year == 2024
        assert dataset.metadata.date.month == 12
        assert dataset.metadata.date.day == 21

    def test_player_jersey_numbers(
        self, meta_data: Path, raw_data: Path
    ) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        home_team = dataset.metadata.teams[0]

        gk = home_team.get_player_by_jersey_number(1)
        assert gk is not None
        assert gk.player_id == "50999"

    def test_player_starting_status(
        self, meta_data: Path, raw_data: Path
    ) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        home_team = dataset.metadata.teams[0]

        starters = [p for p in home_team.players if p.starting]
        non_starters = [p for p in home_team.players if not p.starting]

        assert len(starters) == 11
        assert len(non_starters) == 7

    def test_coordinate_system(self, meta_data: Path, raw_data: Path) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        from kloppy.domain import CDFCoordinateSystem

        assert isinstance(
            dataset.metadata.coordinate_system, CDFCoordinateSystem
        )

        pitch_dims = dataset.metadata.pitch_dimensions
        assert pitch_dims.x_dim.min == -52.5
        assert pitch_dims.x_dim.max == 52.5
        assert pitch_dims.y_dim.min == -34.0
        assert pitch_dims.y_dim.max == 34.0

        assert pitch_dims.pitch_length == 105
        assert pitch_dims.pitch_width == 68

    def test_orientation_static_home_away(
        self, meta_data: Path, raw_data: Path
    ) -> None:
        dataset = cdf.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            only_alive=False,
            coordinates="cdf",
        )

        assert dataset.metadata.orientation == Orientation.STATIC_HOME_AWAY
