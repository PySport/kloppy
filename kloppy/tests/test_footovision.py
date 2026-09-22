from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path

import pytest

from kloppy import footovision
from kloppy.domain import (
    BallState,
    BodyPart,
    BodyPartQualifier,
    DatasetFlag,
    DatasetType,
    EventDataset,
    EventType,
    Orientation,
    PassResult,
    Point,
    PositionType,
    Provider,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TrackingDataset,
)
from kloppy.domain.models.common import ProviderCoordinateSystem
from kloppy.domain.services.event_factory import EventFactory
from kloppy.infra.serializers.event.footovision import (
    FootovisionEventDataDeserializer,
)
from kloppy.infra.serializers.event.footovision.specification import (
    FootovisionPassEvent,
    FootovisionShotEvent,
)
from kloppy.infra.serializers.tracking.footovision import (
    FootovisionTrackingDeserializer,
)


class TestFootovisionEventData:
    """"""

    @pytest.mark.parametrize(
        "tags, expected",
        [
            ([14, 12], [SetPieceType.PENALTY]),
            ([14, 12, 9], [SetPieceType.PENALTY]),
            ([14, 9], [SetPieceType.FREE_KICK]),
            ([14], []),
        ],
    )
    def test_shot_set_piece_qualifiers(self, tags, expected):
        shot = FootovisionShotEvent({"eventTypeIds": tags})
        assert [
            qualifier.value
            for qualifier in shot.get_shot_qualifiers()
            if isinstance(qualifier, SetPieceQualifier)
        ] == expected

    def test_penalty_tag_does_not_qualify_pass(self):
        event = FootovisionPassEvent({"eventTypeIds": [11, 12]})
        assert (
            SetPieceQualifier(SetPieceType.PENALTY)
            not in event.get_pass_qualifiers()
        )

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/footovision_events.json"

    @pytest.fixture
    def meta_data(self, base_dir) -> str:
        return base_dir / "files/footovision_game.json"

    @pytest.fixture
    def dataset(self, event_data: Path, meta_data: Path):
        event_factory = EventFactory()
        return footovision.load_event(
            event_data=event_data,
            meta_data=meta_data,
            additional_metadata={},
            event_factory=event_factory,
        )

    def test_correct_event_data_deserialization(self, dataset: EventDataset):
        assert dataset.metadata.provider == Provider.FOOTOVISION
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.pitch_dimensions.pitch_length == 105.0
        assert dataset.metadata.pitch_dimensions.pitch_width == 68.0
        assert dataset.metadata.attributes["source_pitch_dimensions"] == {
            "length": 105.0,
            "width": 68.0,
            "unit": "meters",
        }

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        # Every raw record is retained, plus 9 substitutions and 4 tactical updates.
        assert len(dataset.events) == 12743 + 9 + 4
        own_goal = next(
            event
            for event in dataset.events
            if event.result == ShotResult.OWN_GOAL
        )
        assert own_goal.raw_event["id"] == 6742527418

        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(0)
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            milliseconds=3020240
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(0)
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            milliseconds=3134280
        )

        # Check the timestamps
        assert dataset.events[0].timestamp == timedelta(seconds=0)
        assert dataset.events[1].timestamp == timedelta(0)
        assert dataset.events[0].event_type == EventType.GENERIC
        assert dataset.events[0].player is None

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "10668"
        assert player.jersey_no == 1
        assert str(player) == "BART VERBRUGGEN"
        assert player.starting_position == PositionType.Goalkeeper

        # Check the qualifiers
        completed_pass = next(
            event
            for event in dataset.events
            if event.raw_event["id"] == 6742527227
        )
        assert completed_pass.result == PassResult.COMPLETE
        assert completed_pass.receiver_player.player_id == "21662"

        header_pass = next(
            event
            for event in dataset.events
            if event.raw_event["id"] == 6742527231
        )
        assert (
            header_pass.get_qualifier_value(BodyPartQualifier) == BodyPart.HEAD
        )

        assert dataset.events[0].coordinates == Point(0.5, 0)

        offside_passes = [
            e
            for e in dataset.events
            if e.event_type == EventType.PASS and e.result == PassResult.OFFSIDE
        ]
        assert {e.event_id for e in offside_passes} == {
            "6742528421",
            "6742529169",
            "6742529200",
        }
        assert (
            sum(e.event_type == EventType.PASS for e in dataset.events) == 906
        )
        for event in offside_passes:
            assert 11 not in event.raw_event["eventTypeIds"]
            assert len(event.related_event_ids) == 1
            offside = dataset.get_event_by_id(event.related_event_ids[0])
            assert 408 in offside.raw_event["eventTypeIds"]
            assert offside.team == event.team
            assert event.event_id in offside.related_event_ids

        substitutions = [
            e for e in dataset.events if e.event_type == EventType.SUBSTITUTION
        ]
        changes = [
            e
            for e in dataset.events
            if e.event_type == EventType.FORMATION_CHANGE
        ]
        assert len(substitutions) == 9
        assert len(changes) == 4
        assert sum(e.state["formation_system_changed"] for e in changes) == 2
        for event in changes:
            assert len(event.player_positions) == 11
            assert event.player is None
            assert event.coordinates is None
        for event in substitutions:
            assert event.player != event.replacement_player
            assert event.replacement_player.team == event.team
            assert event.coordinates is None
            assert event.raw_event["reason"]["playerOut"] == int(
                event.player.player_id
            )
            assert event.raw_event["reason"]["playerIn"] == int(
                event.replacement_player.player_id
            )
            assert len(event.related_event_ids) <= 1
            if event.related_event_ids:
                change = dataset.get_event_by_id(event.related_event_ids[0])
                assert change.event_type == EventType.FORMATION_CHANGE
                assert event.event_id in change.related_event_ids
        assert sum(bool(e.related_event_ids) for e in substitutions) == 5
        assert len({e.event_id for e in dataset.events}) == len(dataset.events)
        times = [(e.period.id, e.timestamp) for e in dataset.events]
        assert times == sorted(times)

    def test_out_of_order_events(self, event_data, meta_data, dataset):
        raw_events = json.loads(event_data.read_text())
        # Reverse timestamp groups, preserving source order within each group.
        raw_events.sort(
            key=lambda event: (event["halftime"], event["startTime"]),
            reverse=True,
        )
        actual = footovision.load_event(
            event_data=BytesIO(json.dumps(raw_events).encode()),
            meta_data=meta_data,
        )
        assert len(actual.events) == len(dataset.events)
        for event, expected in zip(actual.events, dataset.events):
            assert event.event_id == expected.event_id
            assert event.event_type == expected.event_type
            assert event.result == expected.result
            assert event.related_event_ids == expected.related_event_ids
        assert len(actual.metadata.periods) == len(dataset.metadata.periods)
        for period, expected in zip(
            actual.metadata.periods, dataset.metadata.periods
        ):
            assert period.start_timestamp == expected.start_timestamp
            assert period.end_timestamp == expected.end_timestamp

        # Tied kickoff records retain their source order, not an ID-based order.
        kickoff_ids = [
            str(event["id"])
            for event in raw_events
            if event["halftime"] == 1 and event["startTime"] == 0
        ]
        assert [
            event.event_id
            for event in actual.events
            if event.event_id in kickoff_ids
        ] == kickoff_ids

    def test_period_bounds_include_overlapping_events(self):
        raw_events = [
            {"halftime": 2, "startTime": 200, "endTime": 300},
            {"halftime": 1, "startTime": 100, "endTime": 200},
            {"halftime": 1, "startTime": 0, "endTime": 500},
            {"halftime": 2, "startTime": 0, "endTime": 400},
        ]
        periods = FootovisionEventDataDeserializer().create_periods(raw_events)
        assert [period.id for period in periods] == [1, 2]
        assert all(period.start_timestamp == timedelta(0) for period in periods)
        assert periods[0].end_timestamp == timedelta(milliseconds=500)
        assert periods[1].end_timestamp == timedelta(milliseconds=400)

    @pytest.mark.parametrize("period_id", [1, 2])
    def test_rejects_nonzero_period_start(self, period_id):
        raw_events = [
            {"halftime": 1, "startTime": 0, "endTime": 1000},
            {"halftime": 2, "startTime": 0, "endTime": 1000},
        ]
        raw_events[period_id - 1]["startTime"] = 40

        with pytest.raises(
            ValueError,
            match=f"Footovision period {period_id} must start at 0 ms; first timestamp is 40 ms",
        ):
            FootovisionEventDataDeserializer().create_periods(raw_events)

    def test_metric_coordinates(self, event_data: Path, meta_data: Path):
        dataset = footovision.load_event(
            event_data=event_data,
            meta_data=meta_data,
            coordinates="secondspectrum",
        )
        assert (
            dataset.metadata.coordinate_system.provider
            == Provider.SECONDSPECTRUM
        )
        assert dataset.metadata.pitch_dimensions.pitch_length == 105.0
        assert dataset.metadata.pitch_dimensions.pitch_width == 68.0
        # The normalized position (0.5, 0) is the upper touchline midpoint.
        assert dataset.events[0].coordinates.x == pytest.approx(0.0)
        assert dataset.events[0].coordinates.y == pytest.approx(34.0)

        for point, expected in (
            (dataset.find("pass").receiver_coordinates, (-41.685, 34.0)),
            (dataset.find("shot").result_coordinates, (-52.5, 3.332)),
            (dataset.find("carry").end_coordinates, (-11.235, 32.232)),
        ):
            assert (point.x, point.y) == pytest.approx(expected)

    # def test_correct_normalized_event_data_deserialization(
    #     self, event_data: Path, meta_data: Path
    # ):
    #     dataset = sportec.load_event(event_data=event_data, meta_data=meta_data)

    #     assert dataset.events[0].coordinates == Point(0.5641, 0.0)

    # def test_pass_receiver_coordinates(self, dataset: EventDataset):
    #     """Pass receiver_coordinates must match the X/Y-Source-Position of next event"""
    #     first_pass = dataset.find("pass")
    #     assert first_pass.receiver_coordinates != first_pass.next().coordinates
    #     assert first_pass.receiver_coordinates == Point(x=77.75, y=38.71)


class TestFootovisionTrackingData:
    @pytest.mark.parametrize("period_id", [1, 2])
    def test_rejects_nonzero_period_start(self, period_id):
        records = [{"halftime": 1, "time": 0}, {"halftime": 2, "time": 0}]
        records[period_id - 1]["time"] = 40

        with pytest.raises(
            ValueError,
            match=f"Footovision period {period_id} must start at 0 ms; first timestamp is 40 ms",
        ):
            FootovisionTrackingDeserializer().create_periods(records, records)

    @pytest.fixture(scope="class")
    def tracking_paths(self) -> tuple[Path, Path]:
        base_dir = Path(__file__).parent / "files"
        return (
            base_dir / "footovision_game.json",
            base_dir / "footovision_small_tracking.json",
        )

    @pytest.fixture(scope="class")
    def dataset(self, tracking_paths: tuple[Path, Path]) -> TrackingDataset:
        meta_data, raw_data = tracking_paths
        return footovision.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates=Provider.FOOTOVISION,
        )

    def test_metadata(self, dataset: TrackingDataset):
        metadata = dataset.metadata

        assert dataset.dataset_type == DatasetType.TRACKING
        assert metadata.provider == Provider.FOOTOVISION
        assert isinstance(metadata.coordinate_system, ProviderCoordinateSystem)
        assert metadata.coordinate_system.provider == Provider.FOOTOVISION
        assert metadata.frame_rate == 25
        assert metadata.orientation == Orientation.HOME_AWAY
        assert metadata.flags == (
            DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM
        )
        assert metadata.game_id == "28116"
        assert metadata.game_week == "31"
        assert metadata.score is not None
        assert metadata.score.home == 2
        assert metadata.score.away == 1
        assert metadata.date == datetime(
            2026, 3, 21, 12, 45, tzinfo=timezone.utc
        )
        pitch_dimensions = metadata.pitch_dimensions
        assert pitch_dimensions.x_dim.min == 0
        assert pitch_dimensions.x_dim.max == 1
        assert pitch_dimensions.y_dim.min == 0
        assert pitch_dimensions.y_dim.max == 1
        assert pitch_dimensions.pitch_length is not None
        assert pitch_dimensions.pitch_width is not None
        assert pitch_dimensions.pitch_length == pytest.approx(105.0)
        assert pitch_dimensions.pitch_width == pytest.approx(68.0)
        assert metadata.attributes is not None
        assert metadata.attributes["source_pitch_dimensions"] == {
            "length": 105.0,
            "width": 68.0,
            "unit": "meters",
        }
        assert metadata.officials is not None
        assert len(metadata.officials) == 1
        assert metadata.officials[0].official_id == "17341"
        assert metadata.officials[0].name == "DARREN ENGLAND"

    def test_periods_teams_players_and_formations(
        self, dataset: TrackingDataset
    ):
        metadata = dataset.metadata
        home_team, away_team = metadata.teams

        assert [
            (period.id, period.start_timestamp, period.end_timestamp)
            for period in metadata.periods
        ] == [
            (1, timedelta(0), timedelta(seconds=100)),
            (2, timedelta(0), timedelta(seconds=100)),
        ]
        assert (home_team.team_id, home_team.name, len(home_team.players)) == (
            "414",
            "BRIGHTON",
            16,
        )
        assert (away_team.team_id, away_team.name, len(away_team.players)) == (
            "78",
            "LIVERPOOL",
            15,
        )
        assert home_team.starting_formation is not None
        assert away_team.starting_formation is not None
        assert home_team.starting_formation.value == "4-2-3-1"
        assert away_team.starting_formation.value == "4-1-2-1-2"
        assert len(home_team.formations.items) == 4
        assert len(away_team.formations.items) == 4

        player = home_team.get_player_by_id("14584")
        assert player is not None
        assert player.name == "FERDI KADIOGLU"
        assert player.jersey_no == 24
        assert player.starting is True
        assert player.starting_position == PositionType.LeftBack
        assert player.attributes["source_position"] == "FULL_BACK_LEFT"
        assert player.attributes["playing_time"] == 6156320
        assert len(player.positions.items) == 4
        assert player.positions.last() == PositionType.LeftWingBack
        assert metadata.attributes is not None
        assert metadata.attributes["formation_changes"]["home"][0][
            "reason"
        ] == [{"type": "starting XI"}]

    def test_position_history_survives_dataset_operations(self, tracking_paths):
        meta_data, raw_data = tracking_paths
        dataset = footovision.load_tracking(
            meta_data=meta_data, raw_data=raw_data, limit=1
        )
        expected = [
            (1, timedelta(0), PositionType.LeftCentralMidfield),
            (1, timedelta(milliseconds=463160), PositionType.RightForward),
            (2, timedelta(milliseconds=1061680), PositionType.RightForward),
            (
                2,
                timedelta(milliseconds=1857560),
                PositionType.AttackingMidfield,
            ),
        ]

        for result in (
            dataset,
            dataset.transform(to_orientation=Orientation.AWAY_HOME),
            dataset.filter(lambda frame: True),
            dataset.map(lambda frame: frame),
        ):
            player = result.metadata.teams[1].get_player_by_id("11573")
            assert [
                (time.period.id, time.timestamp, position)
                for time, position in player.positions.items.items()
            ] == expected

    def test_missing_position_history_initializes_starters(
        self, tracking_paths
    ):
        meta_data, raw_data = tracking_paths
        metadata = json.loads(meta_data.read_text())
        metadata["homeTeamFormations"] = []
        dataset = footovision.load_tracking(
            meta_data=BytesIO(json.dumps(metadata).encode()),
            raw_data=raw_data,
            limit=1,
        )

        for player in dataset.metadata.teams[0].players:
            if player.starting:
                assert list(player.positions.items.items()) == [
                    (
                        dataset.metadata.periods[0].start_time,
                        player.starting_position,
                    )
                ]
            else:
                assert not player.positions.items

    def test_frames_and_player_data(self, dataset: TrackingDataset):
        assert len(dataset.frames) == 5002

        frame = dataset.frames[0]
        home_team, away_team = dataset.metadata.teams
        player = home_team.get_player_by_id("14584")

        assert frame.frame_id == 0
        assert frame.period is not None
        assert frame.period.id == 1
        assert frame.timestamp == timedelta(0)
        assert frame.ball_coordinates == Point(0.499, 0.498)
        assert frame.ball_speed == 7.13
        assert frame.ball_state == BallState.ALIVE
        assert frame.ball_owning_team == away_team
        assert len(frame.players_data) == 22
        assert player is not None
        assert frame.players_data[player].coordinates == Point(0.37, 0.307)
        assert frame.players_data[player].speed == 0.0
        assert frame.players_data[player].other_data == {
            "acceleration": 2.58,
            "line": "defence",
        }

        final_frame = dataset.frames[-1]
        assert final_frame.frame_id == 5001
        assert final_frame.period is not None
        assert final_frame.period.id == 2
        assert final_frame.timestamp == timedelta(seconds=100)
        assert final_frame.ball_coordinates == Point(0.43, 0.945)
        assert len(final_frame.players_data) == 22

    def test_metric_coordinates(self, tracking_paths: tuple[Path, Path]):
        meta_data, raw_data = tracking_paths
        dataset = footovision.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates="secondspectrum",
            limit=1,
        )
        player = dataset.metadata.teams[0].get_player_by_id("14584")
        point = dataset.frames[0].players_data[player].coordinates
        # Source (0.37, 0.307), on a 105 by 68 metre pitch with centred axes.
        assert point.x == pytest.approx(-13.65)
        assert point.y == pytest.approx(13.124)

    def test_loading_options(self, tracking_paths: tuple[Path, Path]):
        meta_data, raw_data = tracking_paths
        dataset = footovision.load_tracking(
            meta_data=meta_data,
            raw_data=raw_data,
            coordinates=Provider.KLOPPY,
            sample_rate=0.5,
            limit=10,
            only_alive=True,
        )

        assert len(dataset.frames) == 10
        assert isinstance(
            dataset.metadata.coordinate_system, ProviderCoordinateSystem
        )
        assert dataset.metadata.coordinate_system.provider == Provider.KLOPPY
        assert [frame.frame_id for frame in dataset.frames[:3]] == [0, 2, 4]
        assert [frame.timestamp for frame in dataset.frames[:3]] == [
            timedelta(0),
            timedelta(milliseconds=80),
            timedelta(milliseconds=160),
        ]
        assert all(
            frame.ball_state == BallState.ALIVE for frame in dataset.frames
        )


# class TestSportecTrackingData:
#     """
#     Tests for loading Sportec tracking data.
#     """

#     @pytest.fixture
#     def raw_data(self, base_dir) -> str:
#         return base_dir / "files/sportec_positional.xml"

#     @pytest.fixture
#     def raw_data_referee(self, base_dir) -> str:
#         return base_dir / "files/sportec_positional_w_referee.xml"

#     @pytest.fixture
#     def meta_data(self, base_dir) -> str:
#         return base_dir / "files/sportec_meta.xml"

#     @pytest.fixture
#     def dataset(self, raw_data: Path, meta_data: Path) -> TrackingDataset:
#         return sportec.load_tracking(
#             raw_data=raw_data,
#             meta_data=meta_data,
#             coordinates="sportec",
#             limit=None,
#             only_alive=False,
#         )

#     def test_load_metadata(self, dataset: TrackingDataset):
#         assert dataset.metadata.provider == Provider.SPORTEC
#         assert dataset.dataset_type == DatasetType.TRACKING
#         assert len(dataset.metadata.periods) == 2
#         assert dataset.metadata.periods[0].id == 1
#         assert dataset.metadata.periods[0].start_timestamp == timedelta(
#             seconds=400
#         )
#         assert dataset.metadata.periods[0].end_timestamp == timedelta(
#             seconds=400 + 2786.2
#         )
#         assert dataset.metadata.periods[1].id == 2
#         assert dataset.metadata.periods[1].start_timestamp == timedelta(
#             seconds=4000
#         )
#         assert dataset.metadata.periods[1].end_timestamp == timedelta(
#             seconds=4000 + 2996.68
#         )
#         assert len(dataset.metadata.officials) == 4

#     def test_enriched_metadata(self, dataset: TrackingDataset):
#         date = dataset.metadata.date
#         if date:
#             assert isinstance(date, datetime)
#             assert date == datetime(
#                 2020, 6, 5, 18, 30, 0, 210000, tzinfo=timezone.utc
#             )

#         game_week = dataset.metadata.game_week
#         if game_week:
#             assert isinstance(game_week, str)
#             assert game_week == "30"

#         game_id = dataset.metadata.game_id
#         if game_id:
#             assert isinstance(game_id, str)
#             assert game_id == "DFL-MAT-003BN1"

#         home_coach = dataset.metadata.teams[0].coach
#         if home_coach:
#             assert isinstance(home_coach, str)
#             assert home_coach == "C. Streich"

#         away_coach = dataset.metadata.teams[1].coach
#         if away_coach:
#             assert isinstance(away_coach, str)
#             assert away_coach == "M. Rose"

#     def test_load_frames(self, dataset: TrackingDataset):
#         home_team, away_team = dataset.metadata.teams

#         # It load all frames
#         assert len(dataset) == 202

#         # Check frame ids
#         frame_p1_kick_off = dataset.get_record_by_id(10000)
#         assert frame_p1_kick_off is not None
#         frame_p2_kick_off = dataset.get_record_by_id(100000)
#         assert frame_p2_kick_off is not None

#         # Timestamp should be 0.0 for both kick-offs
#         assert frame_p1_kick_off.timestamp == timedelta(seconds=0)
#         assert frame_p2_kick_off.timestamp == timedelta(seconds=0)

#         # Check ball properties
#         assert frame_p1_kick_off.ball_state == BallState.DEAD
#         assert frame_p1_kick_off.ball_owning_team == away_team
#         assert frame_p1_kick_off.ball_coordinates == Point3D(
#             x=2.69, y=0.26, z=0.06
#         )
#         assert dataset.frames[1].ball_speed == 65.59
#         assert dataset.frames[1].ball_owning_team == home_team
#         assert dataset.frames[1].ball_state == BallState.ALIVE

#         # Check player coordinates
#         player_lilian = away_team.get_player_by_id("DFL-OBJ-002G3I")
#         player_data_p1_kick_off = frame_p1_kick_off.players_data[player_lilian]
#         assert player_data_p1_kick_off.coordinates == Point(x=0.35, y=-25.26)
#         player_data_p2_kick_off = frame_p2_kick_off.players_data[player_lilian]
#         assert player_data_p2_kick_off.coordinates == Point(x=-3.91, y=14.1)

#         # We don't load distance right now as it doesn't
#         # work together with `sample_rate`: "The distance covered from the previous frame in cm"
#         assert player_data_p1_kick_off.distance is None

#         # Appears first in 27th frame
#         player_bensebaini = away_team.get_player_by_id("DFL-OBJ-002G5S")
#         assert player_bensebaini not in dataset.frames[0].players_data
#         assert player_bensebaini in dataset.frames[26].players_data

#         # Contains all 3 players
#         assert len(dataset.frames[35].players_data) == 3

#     def test_load_only_alive_frames(self, raw_data: Path, meta_data: Path):
#         dataset = sportec.load_tracking(
#             raw_data=raw_data,
#             meta_data=meta_data,
#             coordinates="sportec",
#             only_alive=True,
#         )
#         assert len(dataset) == 199
#         assert len(dataset.records[2].players_data.keys()) == 1

#     def test_limit_sample(self, raw_data: Path, meta_data: Path):
#         dataset = sportec.load_tracking(
#             raw_data=raw_data,
#             meta_data=meta_data,
#             coordinates="sportec",
#             only_alive=True,
#             limit=100,
#         )
#         assert len(dataset.records) == 100

#         dataset = sportec.load_tracking(
#             raw_data=raw_data,
#             meta_data=meta_data,
#             coordinates="sportec",
#             only_alive=True,
#             limit=100,
#             sample_rate=(1 / 2),
#         )
#         assert len(dataset.records) == 100

#     def test_referees(self, raw_data_referee: Path, meta_data: Path):
#         dataset = sportec.load_tracking(
#             raw_data=raw_data_referee,
#             meta_data=meta_data,
#             coordinates="sportec",
#             only_alive=True,
#         )
#         assert len(dataset.metadata.officials) == 4

#         assert (
#             Official(
#                 official_id="42",
#                 name="Pierluigi Collina",
#                 role=OfficialType.MainReferee,
#             ).role.value
#             == "Main Referee"
#         )

#         assert (
#             Official(
#                 official_id="42",
#                 name="Pierluigi Collina",
#                 role=OfficialType.MainReferee,
#             ).full_name
#             == "Pierluigi Collina"
#         )
#         assert (
#             Official(
#                 official_id="42",
#                 first_name="Pierluigi",
#                 last_name="Collina",
#                 role=OfficialType.MainReferee,
#             ).full_name
#             == "Pierluigi Collina"
#         )
#         assert (
#             Official(
#                 official_id="42",
#                 last_name="Collina",
#                 role=OfficialType.MainReferee,
#             ).full_name
#             == "Collina"
#         )
#         assert (
#             Official(official_id="42", role=OfficialType.MainReferee).full_name
#             == "main_referee_42"
#         )
#         assert Official(official_id="42").full_name == "official_42"
