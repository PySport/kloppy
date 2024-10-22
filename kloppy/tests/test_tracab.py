from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from kloppy._providers.tracab import (
    identify_deserializer,
    TRACABJSONDeserializer,
    TRACABDatDeserializer,
)
from kloppy.domain import (
    Period,
    AttackingDirection,
    Orientation,
    Provider,
    Point,
    Point3D,
    BallState,
    Team,
    Ground,
    DatasetType,
)

from kloppy import tracab


@pytest.fixture(scope="session")
def json_meta_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta.json"


@pytest.fixture(scope="session")
def json_raw_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_raw.json"


@pytest.fixture(scope="session")
def xml_meta_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta.xml"


@pytest.fixture(scope="session")
def xml_meta2_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta_2.xml"


@pytest.fixture(scope="session")
def xml_meta3_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta_3.xml"


@pytest.fixture(scope="session")
def xml_meta4_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_meta_4.xml"


@pytest.fixture(scope="session")
def dat_raw_data(base_dir: Path) -> Path:
    return base_dir / "files" / "tracab_raw.dat"


def test_correct_auto_recognize_deserialization(
    json_meta_data: Path,
    json_raw_data: Path,
    xml_meta_data: Path,
    dat_raw_data: Path,
):
    tracab_json_deserializer = identify_deserializer(
        meta_data=json_meta_data, raw_data=json_raw_data
    )
    assert tracab_json_deserializer == TRACABJSONDeserializer
    tracab_dat_deserializer = identify_deserializer(
        meta_data=xml_meta_data, raw_data=dat_raw_data
    )
    assert tracab_dat_deserializer == TRACABDatDeserializer


class TestTracabJSONTracking:
    def test_correct_deserialization(
        self, json_meta_data: Path, json_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=json_meta_data,
            raw_data=json_raw_data,
            coordinates="tracab",
            only_alive=False,
            file_format="json",
        )
        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 7
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=73940.32
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=76656.32
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=77684.56
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=80717.32
        )
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )
        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=5270.0, y=27.0)

        player_away_12 = dataset.metadata.teams[1].get_player_by_jersey_number(
            12
        )
        assert dataset.records[0].players_data[
            player_away_12
        ].coordinates == Point(x=-4722.0, y=28.0)
        assert dataset.records[0].ball_state == BallState.DEAD
        assert dataset.records[1].ball_state == BallState.ALIVE
        # Shouldn't this be closer to (0,0,0)?
        assert dataset.records[1].ball_coordinates == Point3D(
            x=2710.0, y=3722.0, z=11.0
        )

        # make sure player data is only in the frame when the player is at the pitch
        assert "12170" in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "12170" not in [
            player.player_id
            for player in dataset.records[6].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, json_meta_data: Path, json_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=json_meta_data, raw_data=json_raw_data, only_alive=False
        )
        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )
        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=1.0019047619047619, y=0.49602941176470583)


class TestTracabDATTracking:
    def test_correct_deserialization(
        self, xml_meta_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta_data,
            raw_data=dat_raw_data,
            coordinates="tracab",
            only_alive=False,
        )

        # Check metadata
        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 7
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=73940, microseconds=320000
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=76656, microseconds=320000
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=77684, microseconds=560000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=80717, microseconds=320000
        )

        # Check frame ids and timestamps
        assert dataset.records[0].frame_id == 1848508
        assert dataset.records[0].timestamp == timedelta(0)
        assert dataset.records[1].frame_id == 1848509
        assert dataset.records[1].timestamp == timedelta(microseconds=40000)
        assert dataset.records[3].frame_id == 1916408
        assert dataset.records[3].timestamp == timedelta(seconds=2716)

        # Check frame data
        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )
        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=5270.0, y=27.0)

        player_away_12 = dataset.metadata.teams[1].get_player_by_jersey_number(
            12
        )
        assert dataset.records[0].players_data[
            player_away_12
        ].coordinates == Point(x=-4722.0, y=28.0)
        assert dataset.records[0].ball_coordinates == Point3D(
            x=2710.0, y=3722.0, z=11.0
        )
        assert dataset.records[0].ball_state == BallState.DEAD
        assert dataset.records[0].ball_owning_team == dataset.metadata.teams[0]

        assert dataset.records[4].ball_owning_team == dataset.metadata.teams[1]

        assert dataset.records[1].ball_state == BallState.ALIVE

        # make sure player data is only in the frame when the player is at the pitch
        assert "12170" in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "12170" not in [
            player.player_id
            for player in dataset.records[6].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, xml_meta_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta_data, raw_data=dat_raw_data, only_alive=False
        )

        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )

        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=1.0019047619047619, y=0.49602941176470583)

        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(
                2023, 12, 15, 20, 32, 20, tzinfo=timezone.utc
            )

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "1"


class TestTracabMeta2:
    def test_correct_deserialization(
        self, xml_meta2_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta2_data,
            raw_data=dat_raw_data,
            coordinates="tracab",
            only_alive=False,
        )

        # Check metadata
        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 7
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=73940, microseconds=320000
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=76656, microseconds=320000
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=77684, microseconds=560000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=80717, microseconds=320000
        )

        # No need to check frames, since we do that in TestTracabDATTracking
        # The only difference in this test is the meta data file structure

        # make sure player data is only in the frame when the player is at the pitch
        assert "home_20" in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "home_20" not in [
            player.player_id
            for player in dataset.records[6].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, xml_meta2_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta2_data, raw_data=dat_raw_data, only_alive=False
        )

        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )

        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=1.0019047619047619, y=0.49602941176470583)


class TestTracabMeta3:
    def test_correct_deserialization(
        self, xml_meta3_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta3_data,
            raw_data=dat_raw_data,
            coordinates="tracab",
            only_alive=False,
        )

        # Check metadata
        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 7
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=73940, microseconds=320000
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=76656, microseconds=320000
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=77684, microseconds=560000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=80717, microseconds=320000
        )

        # No need to check frames, since we do that in TestTracabDATTracking
        # The only difference in this test is the meta data file structure

        # make sure player data is only in the frame when the player is at the pitch
        assert "home_20" in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "home_20" not in [
            player.player_id
            for player in dataset.records[6].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, xml_meta3_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta3_data, raw_data=dat_raw_data, only_alive=False
        )

        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )

        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=1.0019047619047619, y=0.49602941176470583)


class TestTracabMeta4:
    def test_correct_deserialization(
        self, xml_meta4_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta4_data,
            raw_data=dat_raw_data,
            coordinates="tracab",
            only_alive=False,
        )

        # Check metadata
        assert dataset.metadata.provider == Provider.TRACAB
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 7
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=73940, microseconds=320000
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=76656, microseconds=320000
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=77684, microseconds=560000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=80717, microseconds=320000
        )

        # No need to check frames, since we do that in TestTracabDATTracking
        # The only difference in this test is the meta data file structure

        # make sure player data is only in the frame when the player is at the pitch
        assert "12170" in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "12170" not in [
            player.player_id
            for player in dataset.records[6].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, xml_meta4_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta4_data, raw_data=dat_raw_data, only_alive=False
        )

        player_home_1 = dataset.metadata.teams[0].get_player_by_jersey_number(
            1
        )

        assert dataset.records[0].players_data[
            player_home_1
        ].coordinates == Point(x=1.0019047619047619, y=0.49602941176470583)
