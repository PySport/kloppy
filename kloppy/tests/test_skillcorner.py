from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kloppy import skillcorner
from kloppy.domain import (
    BallState,
    DatasetType,
    Orientation,
    Point,
    Point3D,
    Provider,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.tracking import (
    skillcorner as skillcorner_serializer,
)

V2_RAW_DATA = (
    b'[{"possession":{"trackable_object":null,"group":null},'
    b'"frame":10,"data":[],"period":1,"time":"00:01.00"}]'
)


class NonSeekableBytesIO(io.RawIOBase):
    def __init__(self, data: bytes):
        super().__init__()
        self._data = memoryview(data)
        self._position = 0
        self._bytes_read = 0

    def readinto(self, buffer):
        size = min(len(buffer), len(self._data) - self._position)
        if size:
            buffer[:size] = self._data[self._position : self._position + size]
            self._position += size
            self._bytes_read += size
        return size

    @property
    def bytes_read(self) -> int:
        return self._bytes_read

    def readable(self):
        return True

    def seekable(self):
        return False

    def seek(self, offset, whence=io.SEEK_SET):
        raise io.UnsupportedOperation("stream is not seekable")

    def tell(self):
        raise io.UnsupportedOperation("stream is not seekable")


class TestSkillCornerTracking:
    @pytest.fixture
    def temporary_wrapper_capture(self, monkeypatch):
        real_buffered_reader = io.BufferedReader
        captured = {}

        def recording_buffered_reader(raw_adapter):
            buffered = real_buffered_reader(raw_adapter)
            captured["buffered"] = buffered
            captured["raw_adapter"] = raw_adapter
            return buffered

        monkeypatch.setattr(
            skillcorner_serializer,
            "io",
            SimpleNamespace(BufferedReader=recording_buffered_reader),
        )
        return captured

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/skillcorner_match_data.json"

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/skillcorner_structured_data.json"

    @pytest.fixture
    def meta_data_v3(self, base_dir) -> str:
        return base_dir / "files/skillcorner_meta_data.json"

    @pytest.fixture
    def raw_data_v3(self, base_dir) -> str:
        return base_dir / "files/skillcorner_v3_raw_data.jsonl"

    @pytest.fixture
    def raw_data_v3_one_line(self, raw_data_v3: Path) -> bytes:
        return next(
            line
            for line in raw_data_v3.read_bytes().splitlines(keepends=True)
            if json.loads(line).get("period") == 1
        )

    @pytest.fixture
    def raw_data_timestamp(self, base_dir) -> str:
        return base_dir / "files/skillcorner_structured_data_timestamp.json"

    def test_correct_deserialization_timestamp(
        self, raw_data_timestamp: Path, meta_data: Path
    ):
        skillcorner.load(
            meta_data=meta_data,
            raw_data=raw_data_timestamp,
            coordinates="skillcorner",
            include_empty_frames=True,
        )

    def test_correct_deserialization(self, raw_data: Path, meta_data: Path):
        dataset = skillcorner.load(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates="skillcorner",
            include_empty_frames=True,
            only_alive=False,
        )

        assert dataset.metadata.provider == Provider.SKILLCORNER
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 55632
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.AWAY_HOME
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=1411 / 10
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=28944 / 10
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=39979 / 10
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=68076 / 10
        )

        assert dataset.records[0].frame_id == 1411
        assert dataset.records[0].timestamp == timedelta(seconds=0)
        assert dataset.records[27534].frame_id == 39979
        assert dataset.records[27534].timestamp == timedelta(seconds=0)

        # make sure skillcorner ID is used as player ID
        assert dataset.metadata.teams[0].players[0].player_id == "10247"

        # make sure data is loaded correctly
        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[112].players_data[
            home_player
        ].coordinates == Point(x=33.8697315398, y=-9.55742259253)

        away_player = dataset.metadata.teams[1].players[9]
        assert dataset.records[112].players_data[
            away_player
        ].coordinates == Point(x=25.9863082795, y=27.3013598578)

        assert dataset.records[113].ball_coordinates == Point3D(
            x=30.5914728131, y=35.3622277834, z=2.24371228757
        )

        # check that missing ball-z_coordinate is identified as None
        assert dataset.records[150].ball_coordinates == Point3D(
            x=11.6568802848, y=24.7214038909, z=None
        )

        # check that 'ball_z' column is included in to_pandas dataframe
        # frame = _frame_to_pandas_row_converter(dataset.records[150])
        # assert "ball_z" in frame.keys()

        # make sure player data is only in the frame when the player is in view
        assert "home_1" not in [
            player.player_id
            for player in dataset.records[112].players_data.keys()
        ]

        assert "away_1" not in [
            player.player_id
            for player in dataset.records[112].players_data.keys()
        ]

        # are anonymous players loaded correctly?
        home_anon_75 = [
            player
            for player in dataset.records[197].players_data
            if player.player_id == "home_anon_75"
        ]
        assert home_anon_75 == [
            player
            for player in dataset.records[200].players_data
            if player.player_id == "home_anon_75"
        ]

        # is pitch dimension set correctly?
        pitch_dimensions = dataset.metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == -52.5
        assert pitch_dimensions.x_dim.max == 52.5
        assert pitch_dimensions.y_dim.min == -34
        assert pitch_dimensions.y_dim.max == 34

        # Check enriched metadata
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(2019, 11, 9, 17, 30, 0, tzinfo=timezone.utc)

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "2417"

        home_coach = dataset.metadata.teams[0].coach
        if home_coach:
            assert isinstance(home_coach, str)
            assert home_coach == "Hans-Dieter Flick"

        away_coach = dataset.metadata.teams[1].coach
        if away_coach:
            assert isinstance(away_coach, str)
            assert away_coach == "Lucien Favre"

    def test_correct_normalized_deserialization(
        self, meta_data: str, raw_data: str
    ):
        dataset = skillcorner.load(
            meta_data=meta_data, raw_data=raw_data, only_alive=False
        )

        home_player = dataset.metadata.teams[0].players[2]
        assert dataset.records[0].players_data[
            home_player
        ].coordinates == Point(x=0.8225688718076191, y=0.6405503322430883)

    def test_skip_empty_frames(self, meta_data: str, raw_data: str):
        dataset = skillcorner.load(
            meta_data=meta_data,
            raw_data=raw_data,
            include_empty_frames=False,
            only_alive=False,
        )

        assert len(dataset.records) == 34783
        assert dataset.records[0].timestamp == timedelta(seconds=11.2)
        assert dataset.records[-1].ball_state == BallState.ALIVE

    def test_skip_dead_frames(self, meta_data: str, raw_data: str):
        dataset = skillcorner.load(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates="skillcorner",
            include_empty_frames=True,
            only_alive=False,
        )

        assert len(dataset.records) == 55632

        dataset = skillcorner.load(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates="skillcorner",
            include_empty_frames=True,
            only_alive=True,
        )

        assert len(dataset.records) == 40069
        assert all([True for x in dataset if x.ball_state == BallState.ALIVE])

    def test_correct_deserialization_v3(
        self, raw_data_v3: Path, meta_data_v3: Path
    ):
        dataset = skillcorner.load(
            meta_data=meta_data_v3,
            raw_data=raw_data_v3,
            coordinates="skillcorner",
            include_empty_frames=True,
            only_alive=False,
        )

        assert dataset.metadata.provider == Provider.SKILLCORNER
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 27
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=1
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=2, microseconds=200000
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=6097, microseconds=700000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=6099
        )

        assert dataset.records[0].frame_id == 10
        assert dataset.records[0].timestamp == timedelta(seconds=0)
        assert dataset.records[-1].frame_id == 60990
        assert dataset.records[-1].timestamp == timedelta(seconds=3256)

        home_team_gk = dataset.metadata.teams[0].get_player_by_id("133")
        assert home_team_gk.player_id == "133"
        assert dataset.records[10].players_data[
            home_team_gk
        ].coordinates == Point(x=40.46, y=-0.58)

        away_team_gk = dataset.metadata.teams[1].get_player_by_id("76")
        assert away_team_gk.player_id == "76"
        assert dataset.records[10].players_data[
            away_team_gk
        ].coordinates == Point(x=-41.97, y=-0.61)

        assert dataset.records[-1].ball_state == BallState.ALIVE
        assert dataset.records[-2].ball_state == BallState.DEAD

    @staticmethod
    def assert_single_frame_dataset(dataset, frame_id, timestamp):
        assert dataset.metadata.provider == Provider.SKILLCORNER
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 1
        assert dataset.records[0].frame_id == frame_id
        assert dataset.records[0].timestamp == timestamp

    @pytest.mark.parametrize(
        ("seekable", "raw_kind", "data_version", "frame_id", "timestamp"),
        [
            pytest.param(
                True,
                "v2",
                None,
                10,
                timedelta(seconds=1),
                id="seekable-v2-automatic",
            ),
            pytest.param(
                True,
                "v2",
                "V2",
                10,
                timedelta(seconds=1),
                id="seekable-v2-explicit",
            ),
            pytest.param(
                True,
                "v3",
                None,
                10,
                timedelta(0),
                id="seekable-v3-one-line-automatic",
            ),
            pytest.param(
                True,
                "v3",
                "V3",
                10,
                timedelta(0),
                id="seekable-v3-one-line-explicit",
            ),
            pytest.param(
                False,
                "v2",
                None,
                10,
                timedelta(seconds=1),
                id="nonseekable-v2-automatic",
            ),
            pytest.param(
                False,
                "v2",
                "V2",
                10,
                timedelta(seconds=1),
                id="nonseekable-v2-explicit",
            ),
            pytest.param(
                False,
                "v3",
                None,
                10,
                timedelta(0),
                id="nonseekable-v3-automatic",
            ),
            pytest.param(
                False,
                "v3",
                "V3",
                10,
                timedelta(0),
                id="nonseekable-v3-explicit",
            ),
        ],
    )
    def test_direct_stream_loading(
        self,
        seekable,
        raw_kind,
        data_version,
        frame_id,
        timestamp,
        meta_data: Path,
        meta_data_v3: Path,
        raw_data_v3_one_line: bytes,
    ):
        raw_data = V2_RAW_DATA if raw_kind == "v2" else raw_data_v3_one_line
        stream = (
            io.BytesIO(raw_data) if seekable else NonSeekableBytesIO(raw_data)
        )

        dataset = skillcorner.load(
            meta_data=meta_data if raw_kind == "v2" else meta_data_v3,
            raw_data=stream,
            data_version=data_version,
            include_empty_frames=True,
        )

        self.assert_single_frame_dataset(dataset, frame_id, timestamp)
        if not seekable:
            assert stream.bytes_read == len(raw_data)
        assert not stream.closed

    @pytest.mark.parametrize(
        ("raw_data", "message"),
        [
            pytest.param(
                b'[{"frame": 10',
                "Could not parse JSON data",
                id="malformed-json-array",
            ),
            pytest.param(
                b'{"period": 1, "time": "00:01.00", "data": []}\n'
                b'{"period": broken}\n',
                "Could not parse JSONL data",
                id="malformed-jsonl",
            ),
            pytest.param(
                b"not skillcorner data",
                "Could not determine raw data format",
                id="unknown-raw-format",
            ),
        ],
    )
    def test_failure_path_closes_temporary_wrappers(
        self,
        meta_data: Path,
        temporary_wrapper_capture,
        raw_data,
        message,
    ):
        raw_stream = NonSeekableBytesIO(raw_data)
        meta_stream = open(meta_data, "rb")
        no_dataset = object()
        dataset = no_dataset
        try:
            with pytest.raises(DeserializationError) as exc_info:
                dataset = skillcorner.load(
                    meta_data=meta_stream,
                    raw_data=raw_stream,
                )

            assert type(exc_info.value) is DeserializationError
            assert str(exc_info.value) == message
            assert dataset is no_dataset
            assert temporary_wrapper_capture["buffered"].closed
            assert temporary_wrapper_capture["raw_adapter"].closed
            assert not raw_stream.closed
            assert not meta_stream.closed
        finally:
            meta_stream.close()
            raw_stream.close()

    def test_success_path_closes_temporary_wrappers(
        self, meta_data: Path, temporary_wrapper_capture
    ):
        underlying = io.BytesIO(V2_RAW_DATA)
        meta_stream = open(meta_data, "rb")
        try:
            dataset = skillcorner.load(
                meta_data=meta_stream,
                raw_data=underlying,
                include_empty_frames=True,
            )

            self.assert_single_frame_dataset(
                dataset, frame_id=10, timestamp=timedelta(seconds=1)
            )
            assert temporary_wrapper_capture["buffered"].closed
            assert temporary_wrapper_capture["raw_adapter"].closed
            assert not underlying.closed
            assert not meta_stream.closed
        finally:
            meta_stream.close()
            underlying.close()
