from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy import wyscout
from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    DatasetType,
    DuelQualifier,
    DuelType,
    EventDataset,
    EventType,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    Ground,
    Orientation,
    PassQualifier,
    PassResult,
    PassType,
    Point,
    Point3D,
    PositionType,
    Provider,
    Score,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    Time,
    TrackingDataset,
    WyscoutTrackingCoordinateSystem,
)


@pytest.fixture(scope="session")
def event_v2_data(base_dir: Path) -> Path:
    return base_dir / "files" / "wyscout_events_v2.json"


@pytest.fixture(scope="session")
def event_v3_data(base_dir: Path) -> Path:
    return base_dir / "files" / "wyscout_events_v3.json"


def test_correct_auto_recognize_deserialization(
    event_v2_data: Path, event_v3_data: Path
):
    dataset = wyscout.load(event_data=event_v2_data, coordinates="wyscout")
    assert dataset.records[2].coordinates == Point(29.0, 6.0)
    dataset = wyscout.load(event_data=event_v3_data, coordinates="wyscout")
    assert dataset.records[2].coordinates == Point(32.0, 56.0)


def test_load_event(event_v2_data: Path, event_v3_data: Path):
    dataset = wyscout.load_event(
        event_data=event_v2_data, coordinates="wyscout"
    )
    assert dataset.records[2].coordinates == Point(29.0, 6.0)
    dataset = wyscout.load_event(
        event_data=event_v3_data, coordinates="wyscout"
    )
    assert dataset.records[2].coordinates == Point(32.0, 56.0)


def test_load_is_deprecated_alias_of_load_event(event_v2_data: Path):
    with pytest.warns(DeprecationWarning, match="wyscout.load_event"):
        dataset = wyscout.load(event_data=event_v2_data, coordinates="wyscout")
    expected = wyscout.load_event(
        event_data=event_v2_data, coordinates="wyscout"
    )
    assert len(dataset.records) == len(expected.records)
    assert dataset.records[2].coordinates == expected.records[2].coordinates


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


class TestWyscoutTracking:
    """Tests related to deserialization of Wyscout tracking data."""

    @pytest.fixture(scope="class")
    def raw_data(self, base_dir: Path) -> Path:
        return base_dir / "files" / "wyscout_tracking_subset.jsonl"

    @pytest.fixture(scope="class")
    def dataset(self, raw_data: Path) -> TrackingDataset:
        return wyscout.load_tracking(raw_data, coordinates="wyscout")

    def test_metadata(self, dataset: TrackingDataset):
        metadata = dataset.metadata
        assert metadata.provider == Provider.WYSCOUT
        assert dataset.dataset_type == DatasetType.TRACKING
        assert metadata.frame_rate == 25
        assert metadata.game_id == "1000001"
        assert metadata.date == datetime(2000, 1, 1, 15, 0, tzinfo=timezone.utc)
        assert metadata.orientation == Orientation.AWAY_HOME
        assert metadata.pitch_dimensions.pitch_length == 105
        assert metadata.pitch_dimensions.pitch_width == 68
        assert isinstance(
            metadata.coordinate_system, WyscoutTrackingCoordinateSystem
        )

    def test_teams_and_players(self, dataset: TrackingDataset):
        home_team, away_team = dataset.metadata.teams
        assert (home_team.name, home_team.ground) == ("Home Team", Ground.HOME)
        assert (away_team.name, away_team.ground) == ("Away Team", Ground.AWAY)
        assert sorted(p.jersey_no for p in home_team.players) == [
            2, 5, 6, 7, 10, 12, 14, 19, 36, 41,
        ]  # fmt: skip
        assert sorted(p.jersey_no for p in away_team.players) == [
            7, 8, 10, 17, 19, 20, 21, 23, 24, 25,
        ]  # fmt: skip
        assert home_team.get_player_by_id("home_7").jersey_no == 7

    def test_periods(self, dataset: TrackingDataset):
        period_1, period_2 = dataset.metadata.periods
        assert period_1.id == 1
        assert period_1.start_timestamp == timedelta(
            seconds=1, microseconds=407480
        )
        assert period_1.end_timestamp == timedelta(
            seconds=2976, milliseconds=80
        )
        assert period_2.id == 2
        assert period_2.start_timestamp == timedelta(
            seconds=2978, microseconds=816970
        )
        assert period_2.end_timestamp == timedelta(seconds=2979)

    def test_frames_before_period_start_are_skipped(
        self, dataset: TrackingDataset
    ):
        # Frames 1-35 have a period clock of 0 (the period has not started)
        assert len(dataset.records) == 11
        first_frame = dataset.records[0]
        assert first_frame.frame_id == 36
        assert first_frame.period.id == 1
        assert first_frame.timestamp == timedelta(microseconds=32520)

    def test_frame_data(self, dataset: TrackingDataset):
        frame = dataset.records[0]
        assert frame.ball_coordinates == Point3D(7.440929, -2.206211, 0.0)
        assert frame.ball_speed is None
        assert frame.other_data["ball_visibility"] == "VISIBLE"
        assert len(frame.players_data) == 20

        home_team, away_team = dataset.metadata.teams
        player = home_team.get_player_by_id("home_7")
        player_data = frame.players_data[player]
        assert player_data.coordinates == Point(0.326534, 23.844245)
        assert player_data.speed == pytest.approx(0.826103)
        assert player_data.other_data == {
            "vx": -0.660939,
            "vy": -0.495586,
            "visibility": "VISIBLE",
            "confidence": "HIGH",
        }
        assert frame.players_data[
            away_team.get_player_by_id("away_24")
        ].coordinates == Point(-14.711086, -7.554815)

    def test_empty_frames_are_kept(self, dataset: TrackingDataset):
        empty_frame = dataset.records[5]
        assert empty_frame.frame_id == 74402
        assert empty_frame.players_data == {}
        assert empty_frame.ball_coordinates is None

    def test_second_period(self, dataset: TrackingDataset):
        frame = dataset.records[-1]
        assert frame.frame_id == 74475
        assert frame.period.id == 2
        assert frame.timestamp == timedelta(microseconds=183030)
        assert frame.ball_coordinates == Point3D(8.21995, 0.772993, 0.0)

    def test_limit_and_sample_rate(self, raw_data: Path):
        dataset = wyscout.load_tracking(raw_data, limit=3)
        assert [f.frame_id for f in dataset.records] == [36, 37, 38]

        dataset = wyscout.load_tracking(raw_data, sample_rate=1 / 2)
        assert [f.frame_id for f in dataset.records] == [
            36, 38, 40, 74471, 74473, 74475,
        ]  # fmt: skip

    def test_default_coordinate_system(self, raw_data: Path):
        dataset = wyscout.load_tracking(raw_data)
        assert dataset.metadata.coordinate_system.provider == Provider.KLOPPY
        assert dataset.records[0].ball_coordinates == Point3D(
            x=pytest.approx((7.440929 + 52.5) / 105),
            y=pytest.approx((34 + 2.206211) / 68),
            z=0.0,
        )

    def test_custom_pitch_size(self, raw_data: Path):
        dataset = wyscout.load_tracking(
            raw_data, coordinates="wyscout", pitch_length=100, pitch_width=60
        )
        assert dataset.metadata.pitch_dimensions.pitch_length == 100
        assert dataset.metadata.pitch_dimensions.pitch_width == 60


class TestWyscoutTrackingWithMatchData:
    """Tests for tracking data loaded with players and directions data."""

    @pytest.fixture(scope="class")
    def raw_data(self, base_dir: Path) -> Path:
        return base_dir / "files" / "wyscout_tracking_subset.jsonl"

    @pytest.fixture(scope="class")
    def players_data(self, base_dir: Path) -> Path:
        return base_dir / "files" / "wyscout_tracking_players.json"

    @pytest.fixture(scope="class")
    def directions_data(self, base_dir: Path) -> Path:
        return base_dir / "files" / "wyscout_tracking_directions.json"

    @pytest.fixture(scope="class")
    def dataset(self, raw_data, players_data, directions_data):
        return wyscout.load_tracking(
            raw_data,
            players_data=players_data,
            directions_data=directions_data,
            coordinates="wyscout",
        )

    def test_teams(self, dataset: TrackingDataset):
        home_team, away_team = dataset.metadata.teams
        assert (home_team.team_id, home_team.name) == ("1001", "Home Team")
        assert (away_team.team_id, away_team.name) == ("1002", "Away Team")
        assert home_team.ground == Ground.HOME
        assert away_team.ground == Ground.AWAY
        assert len(home_team.players) == 20
        assert len(away_team.players) == 20

    def test_players(self, dataset: TrackingDataset):
        home_team = dataset.metadata.teams[0]
        player = home_team.get_player_by_id("100003")
        assert player.jersey_no == 14
        assert player.name == "H. Player14"
        assert player.first_name == "Home"
        assert player.starting is True
        assert home_team.get_player_by_jersey_number(9).starting is False

    def test_frames_use_named_players(self, dataset: TrackingDataset):
        home_team = dataset.metadata.teams[0]
        player = home_team.get_player_by_jersey_number(7)
        assert player.name == "H. Player7"
        frame = dataset.records[0]
        assert frame.players_data[player].coordinates == Point(
            0.326534, 23.844245
        )
        assert all(p.player_id.isdigit() for p in frame.players_data), (
            "all tracked players should be matched to Wyscout players"
        )

    def test_score_and_orientation(self, dataset: TrackingDataset):
        assert dataset.metadata.score == Score(home=2, away=1)
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_directions_override_inferred_orientation(
        self, raw_data, players_data, tmp_path
    ):
        directions = tmp_path / "directions.json"
        directions.write_text(
            '{"1H": {"leftToRightTeamId": 1001, "rightToLeftTeamId": 1002},'
            '"2H": {"leftToRightTeamId": 1001, "rightToLeftTeamId": 1002}}'
        )
        dataset = wyscout.load_tracking(
            raw_data, players_data=players_data, directions_data=directions
        )
        assert dataset.metadata.orientation == Orientation.STATIC_HOME_AWAY

    def test_players_data_without_directions(self, raw_data, players_data):
        dataset = wyscout.load_tracking(raw_data, players_data=players_data)
        assert dataset.metadata.teams[0].team_id == "1001"
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_directions_without_players_are_ignored(
        self, raw_data, directions_data
    ):
        with pytest.warns(UserWarning, match="directions are ignored"):
            dataset = wyscout.load_tracking(
                raw_data, directions_data=directions_data
            )
        assert dataset.metadata.teams[0].team_id == "home"
        assert dataset.metadata.score is None
