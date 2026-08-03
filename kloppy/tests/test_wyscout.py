from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO, UnsupportedOperation
import json
from pathlib import Path

import pytest

from kloppy import wyscout
import kloppy._providers.wyscout as wyscout_provider
from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    DatasetType,
    DuelQualifier,
    DuelType,
    EventDataset,
    EventFactory,
    EventType,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    Orientation,
    PassQualifier,
    PassResult,
    PassType,
    Point,
    Point3D,
    PositionType,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    Time,
)
from kloppy.infra.serializers.event.wyscout import (
    WyscoutDeserializerV2,
    WyscoutDeserializerV3,
    WyscoutInputs,
)


@pytest.fixture(scope="session")
def event_v2_data(base_dir: Path) -> Path:
    return base_dir / "files" / "wyscout_events_v2.json"


@pytest.fixture(scope="session")
def event_v3_data(base_dir: Path) -> Path:
    return base_dir / "files" / "wyscout_events_v3.json"


class NonSeekableStream(BytesIO):
    def seekable(self) -> bool:
        return False

    def seek(self, *args, **kwargs):
        raise UnsupportedOperation("seek")

    def tell(self):
        raise UnsupportedOperation("tell")


class CountingEventFactory(EventFactory):
    def __init__(self):
        self.pass_calls = 0

    def build_pass(self, **kwargs):
        self.pass_calls += 1
        return super().build_pass(**kwargs)


@pytest.mark.parametrize(
    ("version", "fixture_name", "record_count"),
    [
        ("V2", "event_v2_data", 1835),
        ("V3", "event_v3_data", 1896),
    ],
)
@pytest.mark.parametrize("source_kind", ["path", "seekable", "nonseekable"])
@pytest.mark.parametrize("automatic", [True, False])
def test_parse_once_public_matrix(
    monkeypatch,
    request,
    version,
    fixture_name,
    record_count,
    source_kind,
    automatic,
):
    path = request.getfixturevalue(fixture_name)
    if source_kind == "path":
        source = path
    elif source_kind == "seekable":
        source = BytesIO(path.read_bytes())
    else:
        source = NonSeekableStream(path.read_bytes())

    opened_inputs = []
    opened_streams = []
    parsed_streams = []
    original_open = wyscout_provider.open_as_file
    original_json_load = wyscout_provider.json.load

    @contextmanager
    def counted_open(input_, mode="rb"):
        opened_inputs.append(input_)
        with original_open(input_, mode=mode) as stream:
            opened_streams.append(stream)
            yield stream

    def counted_json_load(stream):
        parsed_streams.append(stream)
        return original_json_load(stream)

    monkeypatch.setattr(wyscout_provider, "open_as_file", counted_open)
    monkeypatch.setattr(wyscout_provider.json, "load", counted_json_load)

    dataset = wyscout.load(
        event_data=source,
        data_version=None if automatic else version,
    )

    assert len(dataset.records) == record_count
    assert opened_inputs == [source]
    assert len(opened_streams) == 1
    assert parsed_streams == opened_streams

    if source_kind != "path":
        assert opened_streams[0] is source
        assert not source.closed
        assert source.read() == b""
        if source_kind == "seekable":
            assert source.tell() == path.stat().st_size


@pytest.mark.parametrize(
    ("version", "fixture_name", "record_count", "coordinates"),
    [
        ("V2", "event_v2_data", 1835, Point(29.0, 6.0)),
        ("V3", "event_v3_data", 1896, Point(32.0, 56.0)),
    ],
)
def test_automatic_and_explicit_semantics_match(
    request, version, fixture_name, record_count, coordinates
):
    path = request.getfixturevalue(fixture_name)

    automatic = wyscout.load(event_data=path, coordinates="wyscout")
    explicit = wyscout.load(
        event_data=path,
        coordinates="wyscout",
        data_version=version,
    )

    assert len(automatic.records) == len(explicit.records) == record_count
    assert automatic.metadata == explicit.metadata
    assert automatic.metadata.periods == explicit.metadata.periods
    assert automatic.to_records() == explicit.to_records()
    assert automatic.records[2].coordinates == coordinates
    assert explicit.records[2].coordinates == coordinates

    automatic_factory = CountingEventFactory()
    explicit_factory = CountingEventFactory()
    automatic_passes = wyscout.load(
        event_data=path,
        event_types=["PASS"],
        event_factory=automatic_factory,
    )
    explicit_passes = wyscout.load(
        event_data=path,
        event_types=["PASS"],
        event_factory=explicit_factory,
        data_version=version,
    )

    assert automatic_passes.to_records() == explicit_passes.to_records()
    assert automatic_factory.pass_calls == explicit_factory.pass_calls
    assert automatic_factory.pass_calls == len(automatic_passes.records)


@pytest.mark.parametrize("data_version", [None, "V2", "V3"])
def test_malformed_json_preserves_error(data_version):
    with pytest.raises(json.JSONDecodeError):
        wyscout.load(BytesIO(b'{"events": invalid}'), data_version=data_version)


@pytest.mark.parametrize(
    ("data_version", "exception", "message"),
    [
        (None, IndexError, "list index out of range"),
        ("V2", ValueError, "not enough values to unpack"),
        ("V3", ValueError, "not enough values to unpack"),
    ],
)
def test_empty_events_preserve_error(data_version, exception, message):
    with pytest.raises(exception, match=message):
        wyscout.load(
            BytesIO(b'{"events": [], "teams": {}}'), data_version=data_version
        )


@pytest.mark.parametrize(
    ("data_version", "exception", "message"),
    [
        (
            None,
            ValueError,
            "Wyscout data version could not be recognized, please specify",
        ),
        ("V2", KeyError, "eventName"),
        ("V3", KeyError, "primary"),
    ],
)
def test_unknown_schema_preserves_error(data_version, exception, message):
    data = b'{"events": [{"type": {}}], "teams": {}}'
    with pytest.raises(exception, match=message):
        wyscout.load(BytesIO(data), data_version=data_version)


@pytest.mark.parametrize("data_version", ["v2", "V4", "", "unexpected"])
def test_nonstandard_version_uses_automatic_fallback(
    event_v2_data, data_version
):
    dataset = wyscout.load(event_v2_data, data_version=data_version)
    assert len(dataset.records) == 1835


@pytest.mark.parametrize(
    ("version", "fixture_name"),
    [("V2", "event_v2_data"), ("V3", "event_v3_data")],
)
def test_reusing_consumed_stream_preserves_error(
    request, version, fixture_name
):
    stream = BytesIO(request.getfixturevalue(fixture_name).read_bytes())

    wyscout.load(stream, data_version=version)

    with pytest.raises(json.JSONDecodeError):
        wyscout.load(stream, data_version=version)
    assert not stream.closed


@pytest.mark.parametrize(
    ("deserializer_class", "fixture_name"),
    [
        (WyscoutDeserializerV2, "event_v2_data"),
        (WyscoutDeserializerV3, "event_v3_data"),
    ],
)
def test_parsed_inputs_keep_base_metadata_merge(
    request, deserializer_class, fixture_name
):
    parsed_event_data = json.loads(
        request.getfixturevalue(fixture_name).read_bytes()
    )

    dataset = deserializer_class().deserialize(
        WyscoutInputs(event_data=parsed_event_data),
        additional_metadata={"game_id": "override"},
    )

    assert dataset.metadata.game_id == "override"


def test_correct_auto_recognize_deserialization(
    event_v2_data: Path, event_v3_data: Path
):
    dataset = wyscout.load(event_data=event_v2_data, coordinates="wyscout")
    assert dataset.records[2].coordinates == Point(29.0, 6.0)
    dataset = wyscout.load(event_data=event_v3_data, coordinates="wyscout")
    assert dataset.records[2].coordinates == Point(32.0, 56.0)


class TestWyscoutV2:
    """Tests related to deserialization of Wyscout V2 data."""

    @pytest.fixture(scope="class")
    def dataset(self, event_v2_data) -> EventDataset:
        """Load Wyscout V2 event dataset"""
        dataset = wyscout.load(
            event_data=event_v2_data,
            coordinates="wyscout",
            data_version="V2",
        )
        assert dataset.dataset_type == DatasetType.EVENT
        assert dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        return dataset

    def test_metadata(self, dataset: EventDataset):
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=2863.708369
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=2863.708369
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=2863.708369
        ) + timedelta(seconds=2999.70982)

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "2499773"

    def test_timestamps(self, dataset: EventDataset):
        kickoff_p1 = dataset.get_event_by_id("190078343")
        assert kickoff_p1.timestamp == timedelta(seconds=2.643377)
        kickoff_p2 = dataset.get_event_by_id("190079822")
        assert kickoff_p2.timestamp == timedelta(seconds=0)

    def test_shot_event(self, dataset: EventDataset):
        shot_event = dataset.get_event_by_id("190079151")
        assert (
            shot_event.get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )

    def test_miscontrol_event(self, dataset: EventDataset):
        miscontrol_event = dataset.get_event_by_id("190078351")
        assert miscontrol_event.event_type == EventType.MISCONTROL

    def test_interception_event(self, dataset: EventDataset):
        # A touch or duel with "interception" tag should be converted to an interception event
        interception_event = dataset.get_event_by_id("190079090")
        assert interception_event.event_type == EventType.INTERCEPTION
        # Other events with "interception" tag should be split in two events
        clearance_event = dataset.get_event_by_id("190079171")
        assert clearance_event.event_type == EventType.CLEARANCE
        interception_event = dataset.get_event_by_id("interception-190079171")
        assert interception_event.event_type == EventType.INTERCEPTION

    def test_duel_event(self, dataset: EventDataset):
        ground_duel_event = dataset.get_event_by_id("190078379")
        assert ground_duel_event.event_type == EventType.DUEL
        assert (
            ground_duel_event.get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        aerial_duel_event = dataset.get_event_by_id("190078381")
        assert aerial_duel_event.event_type == EventType.DUEL
        assert (
            aerial_duel_event.get_qualifier_values(DuelQualifier)[1]
            == DuelType.AERIAL
        )
        sliding_tackle_duel_event = dataset.get_event_by_id("190079260")
        assert sliding_tackle_duel_event.event_type == EventType.DUEL
        assert (
            sliding_tackle_duel_event.get_qualifier_values(DuelQualifier)[2]
            == DuelType.SLIDING_TACKLE
        )

    def test_goalkeeper_event(self, dataset: EventDataset):
        goalkeeper_event = dataset.get_event_by_id("190079010")
        assert goalkeeper_event.event_type == EventType.GOALKEEPER
        assert (
            goalkeeper_event.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )

    def test_foul_committed_event(self, dataset: EventDataset):
        foul_committed_event = dataset.get_event_by_id("190079289")
        assert foul_committed_event.event_type == EventType.FOUL_COMMITTED
        assert (
            foul_committed_event.get_qualifier_value(CardQualifier)
            == CardType.FIRST_YELLOW
        )
        card_event = dataset.get_event_by_id("card-190079289")
        assert card_event.event_type == EventType.CARD

    def test_correct_normalized_deserialization(self, event_v2_data: Path):
        dataset = wyscout.load(event_data=event_v2_data, data_version="V2")
        assert dataset.records[2].coordinates == Point(
            0.2981354967264447, 0.06427244582043344
        )


class TestWyscoutV3:
    """Tests related to deserialization of Wyscout V3 data."""

    @pytest.fixture(scope="class")
    def dataset(self, event_v3_data: Path) -> EventDataset:
        """Load Wyscout V3 event dataset"""
        dataset = wyscout.load(
            event_data=event_v3_data,
            coordinates="wyscout",
            data_version="V3",
        )
        assert dataset.dataset_type == DatasetType.EVENT
        assert dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        return dataset

    def test_metadata(self, dataset: EventDataset):
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=0
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            minutes=45, seconds=5
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            minutes=45, seconds=5
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            minutes=45, seconds=5
        ) + timedelta(minutes=46, seconds=58)

        assert (
            dataset.metadata.teams[0].starting_formation
            == FormationType.THREE_FOUR_TWO_ONE
        )

        formation_time_change = Time(
            dataset.metadata.periods[1], timedelta(seconds=3)
        )
        assert (
            dataset.metadata.teams[1].formations.items[formation_time_change]
            == FormationType.FOUR_THREE_ONE_TWO
        )

        second_period_end_time = Time(
            period=dataset.metadata.periods[1],
            timestamp=timedelta(seconds=2818),
        )
        assert (
            dataset.metadata.teams[1].formations.items.keys()[0].period.end_time
            == second_period_end_time
        )

        cr7 = dataset.metadata.teams[0].get_player_by_id("3322")

        assert cr7.full_name == "Cristiano Ronaldo dos Santos Aveiro"
        assert cr7.starting is True
        assert cr7.positions.last() == PositionType.Striker
        assert cr7.jersey_no == 7

    def test_enriched_metadata(self, dataset: EventDataset):
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(2020, 9, 20, 18, 45, tzinfo=timezone.utc)

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "1"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "5154199"

    def test_timestamps(self, dataset: EventDataset):
        kickoff_p1 = dataset.get_event_by_id(1927028854)
        assert kickoff_p1.timestamp == timedelta(minutes=0, seconds=3)
        assert kickoff_p1.time.period.id == 1
        kickoff_p2 = dataset.get_event_by_id(1927029460)
        assert kickoff_p2.timestamp == timedelta(minutes=0, seconds=0)
        assert kickoff_p2.time.period.id == 2

    def test_coordinates(self, dataset: EventDataset):
        assert dataset.records[2].coordinates == Point(32.0, 56.0)

    def test_normalized_deserialization(self, event_v3_data: Path):
        dataset = wyscout.load(event_data=event_v3_data, data_version="V3")
        assert dataset.records[2].coordinates == Point(
            x=0.32643853442316295, y=0.5538235294117646
        )

    def test_pass_event(self, dataset: EventDataset):
        pass_event = dataset.get_event_by_id(1927028486)
        assert pass_event.event_type == EventType.PASS
        assert pass_event.coordinates == Point(x=22.0, y=91.0)
        assert pass_event.receiver_coordinates == Point(x=8.0, y=71.0)

        blocked_pass_event = dataset.get_event_by_id(1927029452)
        assert blocked_pass_event.result == PassResult.INCOMPLETE
        assert blocked_pass_event.coordinates == Point(x=96.0, y=85.0)
        assert blocked_pass_event.receiver_coordinates == Point(x=99.0, y=84.0)

    def test_goalkeeper_event(self, dataset: EventDataset):
        goalkeeper_event = dataset.get_event_by_id(1927029095)
        assert goalkeeper_event.event_type == EventType.GOALKEEPER
        assert (
            goalkeeper_event.get_qualifier_value(GoalkeeperQualifier)
            == GoalkeeperActionType.SAVE
        )

    def test_shot_assist_event(self, dataset: EventDataset):
        shot_assist_event = dataset.get_event_by_id(1927028561)
        assert shot_assist_event.event_type == EventType.PASS
        assert PassType.SHOT_ASSIST in shot_assist_event.get_qualifier_values(
            PassQualifier
        )

    def test_shot_event(self, dataset: EventDataset):
        # a blocked free kick shot
        blocked_shot_event = dataset.get_event_by_id(1927028534)
        assert blocked_shot_event.event_type == EventType.SHOT
        assert blocked_shot_event.result == ShotResult.BLOCKED
        assert blocked_shot_event.result_coordinates == Point(x=77.0, y=21.0)
        assert (
            blocked_shot_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.FREE_KICK
        )
        # off target shot
        off_target_shot = dataset.get_event_by_id(1927028562)
        assert off_target_shot.event_type == EventType.SHOT
        assert off_target_shot.result == ShotResult.OFF_TARGET
        assert off_target_shot.result_coordinates == Point3D(x=100, y=40, z=3.5)
        # on target shot
        on_target_shot = dataset.get_event_by_id(1927028637)
        assert on_target_shot.event_type == EventType.SHOT
        assert on_target_shot.result == ShotResult.SAVED
        assert on_target_shot.result_coordinates == Point3D(x=100, y=45, z=1)

    def test_foul_committed_event(self, dataset: EventDataset):
        foul_committed_event = dataset.get_event_by_id(1927028873)
        assert foul_committed_event.event_type == EventType.FOUL_COMMITTED

    def test_duel_event(self, dataset: EventDataset):
        ground_duel_event = dataset.get_event_by_id(1927028474)
        assert ground_duel_event.event_type == EventType.DUEL
        assert (
            ground_duel_event.get_qualifier_value(DuelQualifier)
            == DuelType.GROUND
        )
        aerial_loose_ball_duel_event = dataset.get_event_by_id(1927028472)
        assert aerial_loose_ball_duel_event.event_type == EventType.DUEL
        assert (
            DuelType.LOOSE_BALL
            in aerial_loose_ball_duel_event.get_qualifier_values(DuelQualifier)
        )
        assert (
            DuelType.AERIAL
            in aerial_loose_ball_duel_event.get_qualifier_values(DuelQualifier)
        )
        sliding_tackle_duel_event = dataset.get_event_by_id(1927028828)
        assert sliding_tackle_duel_event.event_type == EventType.DUEL
        assert (
            DuelType.SLIDING_TACKLE
            in sliding_tackle_duel_event.get_qualifier_values(DuelQualifier)
        )

    def test_clearance_event(self, dataset: EventDataset):
        clearance_event = dataset.get_event_by_id(1927028482)
        assert clearance_event.event_type == EventType.CLEARANCE

    def test_interception_event(self, dataset: EventDataset):
        interception_event = dataset.get_event_by_id(1927028880)
        assert interception_event.event_type == EventType.INTERCEPTION

    def test_take_on_event(self, dataset: EventDataset):
        take_on_event = dataset.get_event_by_id(1927028870)
        assert take_on_event.event_type == EventType.TAKE_ON

    def test_carry_event(self, dataset: EventDataset):
        carry_event = dataset.get_event_by_id(1927028490)
        assert carry_event.event_type == EventType.CARRY
        assert carry_event.end_coordinates == Point(17.0, 4.0)

    def test_formation_change_event(self, dataset: EventDataset):
        assert (
            len(dataset.find_all("formation_change")) == 2
        )  # We shouldn't recognize the change to 4-4-1 as a formation change
        formation_change_event = dataset.get_event_by_id(
            "synthetic-3164-1927029462"
        )
        assert formation_change_event.event_type == EventType.FORMATION_CHANGE
        assert (
            formation_change_event.formation_type
            == FormationType.FOUR_THREE_ONE_TWO
        )

    def test_kick_off_qualifier(self, dataset: EventDataset):
        pass_event_kick_off_first_half = dataset.get_event_by_id(1927028854)
        pass_event_kick_off_second_half = dataset.get_event_by_id(1927029460)
        pass_event_kick_off_after_goal = dataset.get_event_by_id(1927030641)
        assert pass_event_kick_off_first_half.event_type == EventType.PASS
        assert pass_event_kick_off_second_half.event_type == EventType.PASS
        assert pass_event_kick_off_after_goal.event_type == EventType.PASS
        assert (
            SetPieceType.KICK_OFF
            in pass_event_kick_off_first_half.get_qualifier_values(
                SetPieceQualifier
            )
        )
        assert (
            SetPieceType.KICK_OFF
            in pass_event_kick_off_second_half.get_qualifier_values(
                SetPieceQualifier
            )
        )
        assert (
            SetPieceType.KICK_OFF
            in pass_event_kick_off_after_goal.get_qualifier_values(
                SetPieceQualifier
            )
        )

    def test_through_ball_qualifier(self, dataset: EventDataset):
        pass_event = dataset.get_event_by_id(1927028612)
        assert pass_event.event_type == EventType.PASS
        assert PassType.THROUGH_BALL in pass_event.get_qualifier_values(
            PassQualifier
        )

    def test_high_pass_qualifier(self, dataset: EventDataset):
        pass_event = dataset.get_event_by_id(1927028860)
        assert pass_event.event_type == EventType.PASS
        assert PassType.HIGH_PASS in pass_event.get_qualifier_values(
            PassQualifier
        )
