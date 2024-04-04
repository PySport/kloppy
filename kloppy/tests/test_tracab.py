from pathlib import Path
from datetime import timedelta

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
        assert len(dataset.records) == 6
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=100 / 25
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=102 / 25
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=200 / 25
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=202 / 25
        )

        # Check frame ids and timestamps
        assert dataset.records[0].frame_id == 100
        assert dataset.records[0].timestamp == timedelta(seconds=0)
        assert dataset.records[3].frame_id == 200
        assert dataset.records[3].timestamp == timedelta(seconds=0)

        # Check frame data
        player_home_19 = dataset.metadata.teams[0].get_player_by_jersey_number(
            19
        )
        assert dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=-1234.0, y=-294.0)

        player_away_19 = dataset.metadata.teams[1].get_player_by_jersey_number(
            19
        )
        assert dataset.records[0].players_data[
            player_away_19
        ].coordinates == Point(x=8889, y=-666)
        assert dataset.records[0].ball_coordinates == Point3D(x=-27, y=25, z=0)
        assert dataset.records[0].ball_state == BallState.ALIVE
        assert dataset.records[0].ball_owning_team == Team(
            team_id="home", name="home", ground=Ground.HOME
        )

        assert dataset.records[1].ball_owning_team == Team(
            team_id="away", name="away", ground=Ground.AWAY
        )

        assert dataset.records[2].ball_state == BallState.DEAD

        # make sure player data is only in the frame when the player is at the pitch
        assert "away_1337" not in [
            player.player_id
            for player in dataset.records[0].players_data.keys()
        ]
        assert "away_1337" in [
            player.player_id
            for player in dataset.records[3].players_data.keys()
        ]

    def test_correct_normalized_deserialization(
        self, xml_meta_data: Path, dat_raw_data: Path
    ):
        dataset = tracab.load(
            meta_data=xml_meta_data, raw_data=dat_raw_data, only_alive=False
        )

        player_home_19 = dataset.metadata.teams[0].get_player_by_jersey_number(
            19
        )

        assert dataset.records[0].players_data[
            player_home_19
        ].coordinates == Point(x=0.37660000000000005, y=0.5489999999999999)
