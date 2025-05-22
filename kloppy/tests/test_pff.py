from datetime import datetime, timezone
from pathlib import Path

import pytest

from kloppy import pff
from kloppy.domain import DatasetType, Orientation, Point, Point3D, Provider


class TestPFFTracking:
    @pytest.fixture
    def meta_data_home_starts_left(self, base_dir) -> str:
        return base_dir / "files" / "pff_metadata_10517.json"

    @pytest.fixture
    def rosters_meta_data_home_starts_left(self, base_dir) -> str:
        return base_dir / "files" / "pff_rosters_10517.json"

    @pytest.fixture
    def raw_data_home_starts_left(self, base_dir) -> str:
        return base_dir / "files" / "pff_10517.jsonl"

    @pytest.fixture
    def meta_data_home_starts_right(self, base_dir) -> str:
        return base_dir / "files" / "pff_metadata_3812.json"

    @pytest.fixture
    def rosters_meta_data_home_starts_right(self, base_dir) -> str:
        return base_dir / "files" / "pff_rosters_3812.json"

    @pytest.fixture
    def raw_data_home_starts_right(self, base_dir) -> str:
        return base_dir / "files" / "pff_3812.jsonl"

    def test_correct_deserialization_alive_only(
        self,
        raw_data_home_starts_left: Path,
        meta_data_home_starts_left: Path,
        rosters_meta_data_home_starts_left: Path,
    ):
        # Raw data is obtained by grabbing first and last 25 frames of each period
        dataset = pff.load_tracking(
            meta_data=meta_data_home_starts_left,
            roster_meta_data=rosters_meta_data_home_starts_left,
            raw_data=raw_data_home_starts_left,
            coordinates="pff",
            only_alive=True,
        )
        # Check game_id
        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, int)
            assert game_id == 10517

        # Check records size
        assert len(dataset.records) == 199

        # Check periods
        assert len(dataset.metadata.periods) == 4
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[2].id == 3
        assert dataset.metadata.periods[3].id == 4

    def test_correct_deserialization_limit_sample(
        self,
        raw_data_home_starts_left: Path,
        meta_data_home_starts_left: Path,
        rosters_meta_data_home_starts_left: Path,
    ):

        dataset = pff.load_tracking(
            meta_data=meta_data_home_starts_left,
            roster_meta_data=rosters_meta_data_home_starts_left,
            raw_data=raw_data_home_starts_left,
            coordinates="pff",
            only_alive=True,
            limit=100,
        )
        assert len(dataset.records) == 100

        dataset = pff.load_tracking(
            meta_data=meta_data_home_starts_left,
            roster_meta_data=rosters_meta_data_home_starts_left,
            raw_data=raw_data_home_starts_left,
            coordinates="pff",
            only_alive=True,
            limit=100,
            sample_rate=(1 / 2),
        )
        assert len(dataset.records) == 100

    def test_correct_deserialization(
        self,
        raw_data_home_starts_left: Path,
        meta_data_home_starts_left: Path,
        rosters_meta_data_home_starts_left: Path,
    ):
        # Raw data is obtained by grabbing first and last 25 frames of each period
        dataset = pff.load_tracking(
            meta_data=meta_data_home_starts_left,
            roster_meta_data=rosters_meta_data_home_starts_left,
            raw_data=raw_data_home_starts_left,
            coordinates="pff",
            only_alive=False,
        )

        # Check Provider is PFF and DatasetType is Tracking
        assert dataset.metadata.provider == Provider.PFF
        assert dataset.dataset_type == DatasetType.TRACKING

        # Check game_id
        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, int)
            assert game_id == 10517

        # Check records size
        assert len(dataset.records) == 200

        # Check periods
        assert len(dataset.metadata.periods) == 4
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[2].id == 3
        assert dataset.metadata.periods[3].id == 4
        # Check Pitch Dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.5
        assert pitch_dimensions.x_dim.max == 52.5
        assert pitch_dimensions.y_dim.min == -34.0
        assert pitch_dimensions.y_dim.max == 34.0

        # Check Date
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(2022, 12, 18, 15, 0, tzinfo=timezone.utc)

        # Check Orientation
        assert dataset.metadata.orientation == Orientation.HOME_AWAY

        # Check first and last frame of period 1
        assert dataset.records[0].frame_id == 4630
        assert dataset.records[0].timestamp.total_seconds() == 0.000821
        assert dataset.records[49].frame_id == 99119
        assert dataset.records[49].timestamp.total_seconds() == 3152.786941

        # Check first and last frame of period 2
        assert dataset.records[50].frame_id == 100240
        assert dataset.records[50].timestamp.total_seconds() == 0.033011
        assert dataset.records[99].frame_id == 196639
        assert dataset.records[99].timestamp.total_seconds() == 3216.549528

        # Check first and last frame of period 3
        assert dataset.records[100].frame_id == 197541
        assert dataset.records[100].timestamp.total_seconds() == 0.000291
        assert dataset.records[149].frame_id == 226468
        assert dataset.records[149].timestamp.total_seconds() == 965.198823

        # Check first and last frame of period 4
        assert dataset.records[150].frame_id == 230627
        assert dataset.records[150].timestamp.total_seconds() == 0.032929
        assert dataset.records[199].frame_id == 265050
        assert dataset.records[199].timestamp.total_seconds() == 1148.614844

        # Check PFF Home Player
        assert dataset.metadata.teams[0].players[0].player_id == "13222"
        assert dataset.metadata.teams[0].players[0].name == "Nahuel Molina"
        assert dataset.metadata.teams[0].players[0].team.team_id == "364"
        assert dataset.metadata.teams[0].players[0].jersey_no == 26

        # make sure PFF ID is used as player ID for Away Player
        assert dataset.metadata.teams[1].players[0].player_id == "4622"
        assert dataset.metadata.teams[1].players[0].name == "Kingsley Coman"
        assert dataset.metadata.teams[1].players[0].team.team_id == "363"
        assert dataset.metadata.teams[1].players[0].jersey_no == 20

        # Check Home Player coordinates
        home_player = dataset.metadata.teams[0].players[4]  # Julian Alvarez
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=4.987, y=-1.993)

        # Check Away Player coordinates
        away_player = dataset.metadata.teams[1].players[17]  # Olivier Giroud
        assert dataset.records[0].players_data[
            away_player
        ].coordinates == Point(x=0.763, y=-18.099)

        # Check Ball coordinates
        assert dataset.records[0].ball_coordinates == Point3D(
            x=0.42, y=1.59, z=0.39
        )

    def test_orientation(
        self,
        raw_data_home_starts_right: Path,
        meta_data_home_starts_right: Path,
        rosters_meta_data_home_starts_right: Path,
    ):
        # Raw data is obtained by grabbing first and last 25 frames of each period
        dataset = pff.load_tracking(
            meta_data=meta_data_home_starts_right,
            roster_meta_data=rosters_meta_data_home_starts_right,
            raw_data=raw_data_home_starts_right,
            coordinates="pff",
        )

        # Check Orientation
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

        # Check Player name with apostrophe (') in it
        assert dataset.metadata.teams[0].players[1].name == "Moussa N'Diaye"

    def test_correct_normalized_deserialization(
        self,
        raw_data_home_starts_left: Path,
        meta_data_home_starts_left: Path,
        rosters_meta_data_home_starts_left: Path,
    ):
        # Raw data is obtained by grabbing first and last 25 frames of each period
        dataset = pff.load_tracking(
            meta_data=meta_data_home_starts_left,
            roster_meta_data=rosters_meta_data_home_starts_left,
            raw_data=raw_data_home_starts_left,
        )

        # Check Pitch Dimensions
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max == 1
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == 1

        home_player = dataset.metadata.teams[0].players[4]
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=0.547495238095238, y=0.5293088235294118)

        # Check Away Player coordinates
        away_player = dataset.metadata.teams[1].players[17]  # Olivier Giroud
        assert dataset.records[0].players_data[
            away_player
        ].coordinates == Point(x=0.5072666666666666, y=0.7661617647058824)

        # Check Ball coordinates
        assert dataset.records[0].ball_coordinates == Point3D(
            x=0.504, y=0.4766176470588235, z=0.39
        )
