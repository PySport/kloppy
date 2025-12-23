from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from kloppy import sportec
from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    DatasetFlag,
    DatasetType,
    Dimension,
    EventDataset,
    FormationType,
    MetricPitchDimensions,
    Official,
    OfficialType,
    Orientation,
    Origin,
    Point,
    Point3D,
    PositionType,
    Provider,
    Score,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    SportecEventDataCoordinateSystem,
    Time,
    TrackingDataset,
    VerticalOrientation,
)
from kloppy.domain.models.event import EventType


@pytest.fixture(scope="module")
def event_data(base_dir) -> str:
    return base_dir / "files/sportec_events_J03WPY.xml"


@pytest.fixture(scope="module")
def meta_data(base_dir) -> str:
    return base_dir / "files/sportec_meta_J03WPY.xml"


@pytest.fixture(scope="module")
def dataset(event_data: Path, meta_data: Path):
    return sportec.load_event(
        event_data=event_data, meta_data=meta_data, coordinates="sportec"
    )


class TestSportecMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the Sportec provider"""
        assert dataset.metadata.provider == Provider.SPORTEC

    def test_date(self, dataset):
        """It should set the correct match date"""
        assert dataset.metadata.date == datetime.fromisoformat(
            "2022-10-15T11:01:28.300+00:00"
        )

    def test_orientation(self, dataset):
        """It should set the action-executing-team orientation"""
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_frame_rate(self, dataset):
        """It should set the frame rate to None"""
        assert dataset.metadata.frame_rate is None

    def test_teams(self, dataset):
        """It should create the teams and player objects"""
        # There should be two teams with the correct names and starting formations
        assert dataset.metadata.teams[0].name == "Fortuna Düsseldorf"
        assert dataset.metadata.teams[0].coach == "Daniel Thioune"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-2-3-1"
        )
        assert dataset.metadata.teams[1].name == "1. FC Nürnberg"
        assert dataset.metadata.teams[1].coach == "M. Weinzierl"
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-1-3-2"
        )
        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("DFL-OBJ-0000NZ")
        assert player.player_id == "DFL-OBJ-0000NZ"
        assert player.jersey_no == 25
        assert player.full_name == "Matthias Zimmermann"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        # Starting players get their position from the STARTING_XI event
        player = dataset.metadata.teams[0].get_player_by_id("DFL-OBJ-0000NZ")

        assert player.starting_position == PositionType.RightBack
        assert player.starting

        # Substituted players have a position
        sub_player = dataset.metadata.teams[0].get_player_by_id(
            "DFL-OBJ-00008K"
        )
        assert sub_player.starting_position is None
        assert sub_player.positions.last() is not None
        assert not sub_player.starting

        # Get player by position and time
        periods = dataset.metadata.periods
        period_1 = periods[0]
        period_2 = periods[1]

        home_starting_gk = dataset.metadata.teams[0].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_gk.player_id == "DFL-OBJ-0028FW"  # Kastenmeier

        home_starting_cam = dataset.metadata.teams[0].get_player_by_position(
            PositionType.CenterAttackingMidfield,
            time=Time(period=period_1, timestamp=timedelta(seconds=0)),
        )
        assert home_starting_cam.player_id == "DFL-OBJ-002G5J"  # Appelkamp

        home_ending_cam = dataset.metadata.teams[0].get_player_by_position(
            PositionType.CenterAttackingMidfield,
            time=Time(period=period_2, timestamp=timedelta(seconds=45 * 60)),
        )
        assert home_ending_cam.player_id == "DFL-OBJ-00008K"  # Hennings

        away_starting_gk = dataset.metadata.teams[1].get_player_by_position(
            PositionType.Goalkeeper,
            time=Time(period=period_1, timestamp=timedelta(seconds=92)),
        )
        assert away_starting_gk.player_id == "DFL-OBJ-0001HW"  # Mathenia

    def test_periods(self, dataset):
        """It should create the periods"""
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[
            0
        ].start_timestamp == datetime.fromisoformat(
            "2022-10-15T13:01:28.310+02:00"
        )
        assert dataset.metadata.periods[
            0
        ].end_timestamp == datetime.fromisoformat(
            "2022-10-15T13:47:31.000+02:00"
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[
            1
        ].start_timestamp == datetime.fromisoformat(
            "2022-10-15T14:03:29.010+02:00"
        )
        assert dataset.metadata.periods[
            1
        ].end_timestamp == datetime.fromisoformat(
            "2022-10-15T14:54:41.000+02:00"
        )

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        assert dataset.metadata.pitch_dimensions == MetricPitchDimensions(
            x_dim=Dimension(0, 105),
            y_dim=Dimension(0, 68),
            standardized=False,
            pitch_length=105,
            pitch_width=68,
        )

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        coordinate_system = dataset.metadata.coordinate_system
        assert isinstance(coordinate_system, SportecEventDataCoordinateSystem)
        assert coordinate_system.origin == Origin.BOTTOM_LEFT
        assert (
            coordinate_system.vertical_orientation
            == VerticalOrientation.BOTTOM_TO_TOP
        )
        assert coordinate_system.normalized is False

    def test_score(self, dataset):
        """It should set the correct score"""
        assert dataset.metadata.score == Score(0, 1)

    def test_officials(self, dataset):
        """It should set the correct officials"""
        referees = {role: list() for role in OfficialType}
        for referee in dataset.metadata.officials:
            referees[referee.role].append(referee)
        # main referee
        assert referees[OfficialType.MainReferee][0].name == "W. Haslberger"
        assert referees[OfficialType.MainReferee][0].first_name == "Wolfgang"
        assert referees[OfficialType.MainReferee][0].last_name == "Haslberger"
        # assistants
        assert referees[OfficialType.AssistantReferee][0].name == "D. Riehl"
        assert referees[OfficialType.AssistantReferee][1].name == "L. Erbst"
        assert referees[OfficialType.FourthOfficial][0].name == "N. Fuchs"
        assert (
            referees[OfficialType.VideoAssistantReferee][0].name
            == "D. Schlager"
        )

    def test_flags(self, dataset):
        """It should set the correct flags"""
        assert dataset.metadata.flags == DatasetFlag(0)


class TestsSportecCautionEvent:
    """Tests related to deserializing Caution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should create a card event for each Caution event."""
        events = dataset.find_all("card")
        assert len(events) == 9

        for event in events:
            assert event.card_type == CardType.FIRST_YELLOW

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of cards"""
        card = dataset.get_event_by_id("18237400001225")
        # A card should have a card type
        assert card.card_type == CardType.FIRST_YELLOW
        # Card qualifiers should not be added
        assert card.get_qualifier_value(CardQualifier) is None


class TestSportecLegacyEventData:
    """Tests on some old private Sportec event data."""

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/sportec_events.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta.xml"

    @pytest.fixture
    def dataset(self, event_data: Path, meta_data: Path):
        return sportec.load_event(
            event_data=event_data, meta_data=meta_data, coordinates="sportec"
        )

    def test_correct_event_data_deserialization(self, dataset: EventDataset):
        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        assert len(dataset.events) == 29
        assert dataset.events[28].result == ShotResult.OWN_GOAL

        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == datetime(
            2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[0].end_timestamp == datetime(
            2020, 6, 5, 19, 16, 24, 0, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == datetime(
            2020, 6, 5, 19, 33, 27, 10000, tzinfo=timezone.utc
        )
        assert dataset.metadata.periods[1].end_timestamp == datetime(
            2020, 6, 5, 20, 23, 18, 0, tzinfo=timezone.utc
        )

        # Check the timestamps
        assert dataset.events[0].timestamp == timedelta(seconds=0)
        assert dataset.events[1].timestamp == timedelta(seconds=3.123)
        assert dataset.events[25].timestamp == timedelta(seconds=0)

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "DFL-OBJ-00001D"
        assert player.jersey_no == 1
        assert str(player) == "A. Schwolow"
        assert player.starting_position == PositionType.Goalkeeper

        # Check the qualifiers
        assert (
            dataset.events[25].get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )
        assert (
            dataset.events[16].get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )
        assert (
            dataset.events[24].get_qualifier_value(BodyPartQualifier)
            == BodyPart.LEFT_FOOT
        )
        assert (
            dataset.events[26].get_qualifier_value(BodyPartQualifier)
            == BodyPart.HEAD
        )

        assert dataset.events[0].coordinates == Point(56.41, 68.0)

    def test_correct_normalized_event_data_deserialization(
        self, event_data: Path, meta_data: Path
    ):
        dataset = sportec.load_event(event_data=event_data, meta_data=meta_data)

        assert dataset.events[0].coordinates == Point(0.5641, 0.0)

    def test_pass_receiver_coordinates(self, dataset: EventDataset):
        """Pass receiver_coordinates must match the X/Y-Source-Position of next event"""
        first_pass = dataset.find("pass")
        assert first_pass.receiver_coordinates != first_pass.next().coordinates
        assert first_pass.receiver_coordinates == Point(x=77.75, y=38.71)


class TestSportecPublicEventData:
    """"""

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/sportec_events_J03WPY.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta_J03WPY.xml"

    @pytest.fixture
    def dataset(self, event_data: Path, meta_data: Path):
        return sportec.load_event(
            event_data=event_data, meta_data=meta_data, coordinates="sportec"
        )

    def test_correct_event_data_deserialization_new(
        self, dataset: EventDataset
    ):
        """A basic version of the event data deserialization test, for a newer event data file."""
        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        # Test the kloppy event types that are being parsed
        event_types_set = set(event.event_type for event in dataset.events)

        # Kloppy types that were already being deserialized
        assert EventType.SHOT in event_types_set
        assert EventType.PASS in event_types_set
        assert EventType.RECOVERY in event_types_set
        assert EventType.SUBSTITUTION in event_types_set
        assert EventType.CARD in event_types_set
        assert EventType.FOUL_COMMITTED in event_types_set
        assert EventType.GENERIC in event_types_set

        # Kloppy types added in PR #XXXX
        assert EventType.CLEARANCE in event_types_set
        assert EventType.INTERCEPTION in event_types_set
        assert EventType.DUEL in event_types_set
        assert EventType.TAKE_ON in event_types_set

        interceptions = dataset.find_all("interception")
        # All interceptions in the sportec_events_J03WPY.xml are at the end of the file,
        # but should be distributed throughout the match properly by the deserializer
        assert interceptions[0].period.id == 1


class TestSportecTrackingData:
    """
    Tests for loading Sportec tracking data.
    """

    @pytest.fixture
    def raw_data(self, base_dir) -> str:
        return base_dir / "files/sportec_positional.xml"

    @pytest.fixture
    def raw_data_referee(self, base_dir) -> str:
        return base_dir / "files/sportec_positional_w_referee.xml"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/sportec_meta.xml"

    @pytest.fixture
    def dataset(self, raw_data: Path, meta_data: Path) -> TrackingDataset:
        return sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            limit=None,
            only_alive=False,
        )

    def test_load_metadata(self, dataset: TrackingDataset):
        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=400
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=400 + 2786.2
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=4000
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=4000 + 2996.68
        )
        assert len(dataset.metadata.officials) == 4

    def test_enriched_metadata(self, dataset: TrackingDataset):
        date = dataset.metadata.date
        if date:
            assert isinstance(date, datetime)
            assert date == datetime(
                2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
            )

        game_week = dataset.metadata.game_week
        if game_week:
            assert isinstance(game_week, str)
            assert game_week == "30"

        game_id = dataset.metadata.game_id
        if game_id:
            assert isinstance(game_id, str)
            assert game_id == "DFL-MAT-003BN1"

        home_coach = dataset.metadata.teams[0].coach
        if home_coach:
            assert isinstance(home_coach, str)
            assert home_coach == "C. Streich"

        away_coach = dataset.metadata.teams[1].coach
        if away_coach:
            assert isinstance(away_coach, str)
            assert away_coach == "M. Rose"

    def test_load_frames(self, dataset: TrackingDataset):
        home_team, away_team = dataset.metadata.teams

        # It load all frames
        assert len(dataset) == 202

        # Check frame ids
        frame_p1_kick_off = dataset.get_record_by_id(10000)
        assert frame_p1_kick_off is not None
        frame_p2_kick_off = dataset.get_record_by_id(100000)
        assert frame_p2_kick_off is not None

        # Timestamp should be 0.0 for both kick-offs
        assert frame_p1_kick_off.timestamp == timedelta(seconds=0)
        assert frame_p2_kick_off.timestamp == timedelta(seconds=0)

        # Check ball properties
        assert frame_p1_kick_off.ball_state == BallState.DEAD
        assert frame_p1_kick_off.ball_owning_team == away_team
        assert frame_p1_kick_off.ball_coordinates == Point3D(
            x=2.69, y=0.26, z=0.06
        )
        assert dataset.frames[1].ball_speed == 65.59
        assert dataset.frames[1].ball_owning_team == home_team
        assert dataset.frames[1].ball_state == BallState.ALIVE

        # Check player coordinates
        player_lilian = away_team.get_player_by_id("DFL-OBJ-002G3I")
        player_data_p1_kick_off = frame_p1_kick_off.players_data[player_lilian]
        assert player_data_p1_kick_off.coordinates == Point(x=0.35, y=-25.26)
        player_data_p2_kick_off = frame_p2_kick_off.players_data[player_lilian]
        assert player_data_p2_kick_off.coordinates == Point(x=-3.91, y=14.1)

        # We don't load distance right now as it doesn't
        # work together with `sample_rate`: "The distance covered from the previous frame in cm"
        assert player_data_p1_kick_off.distance is None

        # Appears first in 27th frame
        player_bensebaini = away_team.get_player_by_id("DFL-OBJ-002G5S")
        assert player_bensebaini not in dataset.frames[0].players_data
        assert player_bensebaini in dataset.frames[26].players_data

        # Contains all 3 players
        assert len(dataset.frames[35].players_data) == 3

    def test_load_only_alive_frames(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )
        assert len(dataset) == 199
        assert len(dataset.records[2].players_data.keys()) == 1

    def test_limit_sample(self, raw_data: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
            limit=100,
        )
        assert len(dataset.records) == 100

        dataset = sportec.load_tracking(
            raw_data=raw_data,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
            limit=100,
            sample_rate=(1 / 2),
        )
        assert len(dataset.records) == 100

    def test_referees(self, raw_data_referee: Path, meta_data: Path):
        dataset = sportec.load_tracking(
            raw_data=raw_data_referee,
            meta_data=meta_data,
            coordinates="sportec",
            only_alive=True,
        )
        assert len(dataset.metadata.officials) == 4

        assert (
            Official(
                official_id="42",
                name="Pierluigi Collina",
                role=OfficialType.MainReferee,
            ).role.value
            == "Main Referee"
        )

        assert (
            Official(
                official_id="42",
                name="Pierluigi Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Pierluigi Collina"
        )
        assert (
            Official(
                official_id="42",
                first_name="Pierluigi",
                last_name="Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Pierluigi Collina"
        )
        assert (
            Official(
                official_id="42",
                last_name="Collina",
                role=OfficialType.MainReferee,
            ).full_name
            == "Collina"
        )
        assert (
            Official(official_id="42", role=OfficialType.MainReferee).full_name
            == "main_referee_42"
        )
        assert Official(official_id="42").full_name == "official_42"
