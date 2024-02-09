import os
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from kloppy.domain import (
    build_coordinate_system,
    AttackingDirection,
    TakeOnResult,
    Dimension,
    BallState,
    PitchDimensions,
    CardQualifier,
    DatasetFlag,
    CarryResult,
    InterceptionResult,
    SubstitutionEvent,
    BodyPart,
    BodyPartQualifier,
    DatasetType,
    DuelQualifier,
    DuelType,
    DuelResult,
    Orientation,
    PassResult,
    Point,
    Point3D,
    Provider,
    FormationType,
    SetPieceQualifier,
    SetPieceType,
    Position,
    ShotResult,
    EventDataset,
)

from kloppy.exceptions import DeserializationError
from kloppy import statsbomb
from kloppy.domain.models.event import (
    CardType,
    PassQualifier,
    PassType,
    EventType,
    GoalkeeperQualifier,
    GoalkeeperActionType,
)
from kloppy.infra.serializers.event.statsbomb.helpers import (
    parse_str_ts,
)
import kloppy.infra.serializers.event.statsbomb.specification as SB

ENABLE_PLOTTING = True
API_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/"


def test_with_visualization():
    if (
        "KLOPPY_TESTWITHVIZ" in os.environ
        and os.environ["KLOPPY_TESTWITHVIZ"] == "1"
    ):
        return True
    return False


@pytest.fixture(scope="module")
def dataset() -> EventDataset:
    """Load StatsBomb data for Belgium - Portugal at Euro 2020"""
    dataset = statsbomb.load(
        event_data=f"{API_URL}/events/3794687.json",
        lineup_data=f"{API_URL}/lineups/3794687.json",
        three_sixty_data=f"{API_URL}/three-sixty/3794687.json",
        coordinates="statsbomb",
    )
    assert dataset.dataset_type == DatasetType.EVENT
    return dataset


def test_get_enum_type():
    """Test retrieving enum types for StatsBomb IDs"""
    # retrieve by id
    assert SB.EVENT_TYPE(30) == SB.EVENT_TYPE.PASS
    with pytest.raises(
        DeserializationError, match="Unknown StatsBomb Event Type: 0"
    ):
        SB.EVENT_TYPE(0)
    # retrieve by id + name dict
    assert SB.EVENT_TYPE({"id": 30, "name": "pass"}) == SB.EVENT_TYPE.PASS
    with pytest.raises(
        DeserializationError, match="Unknown StatsBomb Event Type: 0/unknown"
    ):
        SB.EVENT_TYPE({"id": 0, "name": "unknown"})
    # the exception message should contain the fully qualified name of the enum
    with pytest.raises(
        DeserializationError,
        match="Unknown StatsBomb Pass Technique: 0/unkown",
    ):
        SB.PASS.TECHNIQUE({"id": 0, "name": "unkown"})


class TestStatsBombMetadata:
    """Tests related to deserializing metadata"""

    def test_provider(self, dataset):
        """It should set the StatsBomb provider"""
        assert dataset.metadata.provider == Provider.STATSBOMB

    def test_orientation(self, dataset):
        """It should set the action-executing-team orientation"""
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )

    def test_framerate(self, dataset):
        """It should set the frame rate to None"""
        assert dataset.metadata.frame_rate is None

    def test_teams(self, dataset):
        """It should create the teams and player objects"""
        # There should be two teams with the correct names and starting formations
        assert dataset.metadata.teams[0].name == "Belgium"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "3-4-2-1"
        )
        assert dataset.metadata.teams[1].name == "Portugal"
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-3-3"
        )
        # The teams should have the correct players
        player = dataset.metadata.teams[0].get_player_by_id("3089")
        assert player.player_id == "3089"
        assert player.jersey_no == 7
        assert str(player) == "Kevin De Bruyne"

    def test_player_position(self, dataset):
        """It should set the correct player position from the events"""
        # Starting players get their position from the STARTING_XI event
        player = dataset.metadata.teams[0].get_player_by_id("3089")
        assert player.position == Position(
            position_id="18", name="Right Attacking Midfield", coordinates=None
        )
        assert player.starting

        # Substituted players don't have a position
        sub_player = dataset.metadata.teams[0].get_player_by_id("5630")
        assert sub_player.position is None
        assert not sub_player.starting

    def test_periods(self, dataset):
        """It should create the periods"""
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == parse_str_ts(
            "00:00:00.000"
        )
        assert dataset.metadata.periods[0].end_timestamp == parse_str_ts(
            "00:47:38.122"
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == parse_str_ts(
            "00:47:38.122"
        )
        assert dataset.metadata.periods[1].end_timestamp == parse_str_ts(
            "00:47:38.122"
        ) + parse_str_ts("00:50:29.638")

    def test_pitch_dimensions(self, dataset):
        """It should set the correct pitch dimensions"""
        assert dataset.metadata.pitch_dimensions == PitchDimensions(
            x_dim=Dimension(0, 120), y_dim=Dimension(0, 80)
        )

    def test_coordinate_system(self, dataset):
        """It should set the correct coordinate system"""
        assert dataset.metadata.coordinate_system == build_coordinate_system(
            Provider.STATSBOMB, width=80, length=120
        )

    @pytest.mark.xfail
    def test_score(self, dataset):
        """It should set the correct score"""
        # TODO: score is not set in the dataset; we could infer it from the
        # events
        assert dataset.metadata.score == (1, 0)

    def test_flags(self, dataset):
        """It should set the correct flags"""
        assert (
            dataset.metadata.flags
            == DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE
        )


class TestStatsBombEvent:
    """Generic tests related to deserializing events"""

    def test_generic_attributes(self, dataset: EventDataset):
        """Test generic event attributes"""
        event = dataset.get_event_by_id("a5c60797-631e-418a-9f24-1e9779cb2b42")
        assert event.event_id == "a5c60797-631e-418a-9f24-1e9779cb2b42"
        assert event.team.name == "Belgium"
        assert event.ball_owning_team.name == "Belgium"
        assert event.player.name == "Thorgan Hazard"
        assert event.coordinates == Point(96.75, 24.65)
        assert event.raw_event["id"] == "a5c60797-631e-418a-9f24-1e9779cb2b42"
        assert event.related_event_ids == [
            "3eb5f3a7-3654-4c85-8880-3ecc741dbb57"
        ]
        assert event.period.id == 1
        assert event.timestamp == parse_str_ts("00:41:31.122")
        assert event.ball_state == BallState.ALIVE

    def test_timestamp(self, dataset):
        """It should set the correct timestamp, reset to zero after each period"""
        kickoff_p1 = dataset.get_event_by_id(
            "8022c113-e349-4b0b-b4a7-a3bb662535f8"
        )
        assert kickoff_p1.timestamp == parse_str_ts("00:00:00.840")
        kickoff_p2 = dataset.get_event_by_id(
            "b3199171-507c-42a3-b4c4-9e609d7a98f6"
        )
        assert kickoff_p2.timestamp == parse_str_ts("00:00:00.848")

    def test_related_events(self, dataset: EventDataset):
        """Test whether related events are properly linked"""
        carry_event = dataset.get_event_by_id(
            "160ae2e4-812f-4161-9521-eafa6ca815bd"
        )
        pass_event = dataset.get_event_by_id(
            "0750ecc5-41f2-4118-a927-1db4870d92ed"
        )
        receipt_event = dataset.get_event_by_id(
            "217ea3ba-ed5d-46ae-96ef-5e3dd7884c7e"
        )

        assert carry_event.get_related_events() == [pass_event, receipt_event]
        assert carry_event.related_pass() == pass_event

    def test_synthetic_out_events(self, dataset: EventDataset):
        """It should add synthetic ball out events"""
        ball_out_events = dataset.find_all("ball_out")
        assert (
            len(ball_out_events) == 26 + 3 + 18
        )  # throw-in + corner + goal kick

        assert ball_out_events[0].ball_state == BallState.DEAD

    def test_freeze_frame_shot(self, dataset: EventDataset, base_dir: Path):
        """Test if shot freeze-frame is properly parsed and attached to shot events"""
        shot_event = dataset.get_event_by_id(
            "a5c60797-631e-418a-9f24-1e9779cb2b42"
        )

        # The freeze-frame should be attached to the shot event
        freeze_frame = shot_event.freeze_frame
        assert freeze_frame is not None

        # The freeze-frame should have the correct frame id
        assert freeze_frame.frame_id == 62278

        # The start location of the shot event should be the same as the
        # location of the player who took the shot in the freeze-frame
        event_player_coordinates = freeze_frame.players_coordinates[
            shot_event.player
        ]
        assert event_player_coordinates == shot_event.coordinates

        # The freeze-frame should contain the location of all players
        player_3089 = dataset.metadata.teams[0].get_player_by_id("3089")
        assert freeze_frame.players_coordinates[player_3089] == Point(
            91.45, 28.15
        )

        if test_with_visualization():
            import matplotlib.pyplot as plt
            from mplsoccer import VerticalPitch

            pitch = VerticalPitch(
                pitch_type="statsbomb",
                pitch_color="white",
                line_color="#c7d5cc",
                half=True,
            )
            _, ax = pitch.draw()

            def get_color(player):
                if player.team == shot_event.player.team:
                    return "#b94b75"
                elif player.position.position_id == "1":
                    return "#c15ca5"
                else:
                    return "#7f63b8"

            x, y, color, label = zip(
                *[
                    (
                        coordinates.x,
                        coordinates.y,
                        get_color(player),
                        player.jersey_no,
                    )
                    for player, coordinates in shot_event.freeze_frame.players_coordinates.items()
                ]
            )

            # plot the players
            _ = pitch.scatter(x, y, color=color, s=100, ax=ax)

            # plot the shot
            _ = pitch.scatter(
                shot_event.coordinates.x,
                shot_event.coordinates.y,
                marker="football",
                s=200,
                ax=ax,
                zorder=1.2,
            )
            _ = pitch.lines(
                shot_event.coordinates.x,
                shot_event.coordinates.y,
                shot_event.result_coordinates.x,
                shot_event.result_coordinates.y,
                comet=True,
                label="shot",
                color="#cb5a4c",
                ax=ax,
            )

            # plot the angle to the goal
            pitch.goal_angle(
                shot_event.coordinates.x,
                shot_event.coordinates.y,
                ax=ax,
                alpha=0.2,
                zorder=1.1,
                color="#cb5a4c",
                goal="right",
            )

            # plot the jersey numbers
            for x, y, label in zip(x, y, label):
                pitch.annotate(
                    label,
                    (x, y),
                    va="center",
                    ha="center",
                    color="#FFF",
                    fontsize=5,
                    ax=ax,
                )

            plt.savefig(
                base_dir / "outputs" / "test_statsbomb_freeze_frame_shot.png"
            )

    def test_freeze_frame_360(self, dataset: EventDataset, base_dir: Path):
        """Test if 360 freeze-frame is properly parsed and attached to shot events"""
        pass_event = dataset.get_event_by_id(
            "8022c113-e349-4b0b-b4a7-a3bb662535f8"
        )

        # The freeze-frame should be attached to the pass event
        freeze_frame = pass_event.freeze_frame
        assert freeze_frame is not None

        # The freeze-frame should have the correct frame id
        assert freeze_frame.frame_id == 21

        # The start location of the pass event should be the same as the
        # location of the player who took the pass in the freeze-frame
        event_player_coordinates = freeze_frame.players_coordinates[
            pass_event.player
        ]
        assert event_player_coordinates == pass_event.coordinates

        # The freeze-frame should contain the location of all players
        coordinates_per_team = defaultdict(list)
        for (
            player,
            coordinates,
        ) in pass_event.freeze_frame.players_coordinates.items():
            coordinates_per_team[player.team.name].append(coordinates)
        assert coordinates_per_team == {
            "Belgium": [
                Point(x=35.99060380081866, y=41.66525336943679),
                Point(x=36.772456745606966, y=56.21011263812901),
                Point(x=38.57361054325343, y=30.6087172186446),
                Point(x=48.67355615368716, y=75.38189207476186),
                Point(x=48.75568346168778, y=3.8633240447865917),
                Point(x=50.95872747765954, y=47.71967220619873),
                Point(x=54.10078267552914, y=42.31688706370833),
                Point(x=58.68224371136122, y=20.546753900071717),
                Point(x=59.40711636358271, y=56.23668960423852),
                Point(x=59.95, y=39.95),
            ],
            "Portugal": [
                Point(x=60.08877666702633, y=51.6228617162824),
                Point(x=60.36328965732384, y=65.29360218855575),
                Point(x=63.31834157832884, y=20.637620280619082),
                Point(x=63.34010422368807, y=30.2461666887323),
                Point(x=69.2595851053029, y=47.82198861375186),
                Point(x=72.3836245120975, y=45.09550017900719),
                Point(x=79.38842007565164, y=29.1873906614789),
                Point(x=79.84460915854939, y=60.932012488317184),
                Point(x=79.86927684616296, y=47.680837988321386),
                Point(x=82.64427177513934, y=35.464836688277295),
            ],
        }

        # The visible area should be stored in "other_data"
        visible_area = pass_event.freeze_frame.other_data["visible_area"]
        assert visible_area == pytest.approx(
            [
                120.0,
                28.02,
                87.93,
                80.0,
                32.71,
                80.0,
                0.0,
                26.78,
                0.0,
                0.0,
                120.0,
                0.0,
                120.0,
                28.02,
            ],
            abs=1e-2,
        )

        if test_with_visualization():
            import matplotlib.pyplot as plt
            from mplsoccer import Pitch

            pitch = Pitch(
                pitch_type="statsbomb",
                pitch_color="white",
                line_color="#c7d5cc",
                half=False,
            )
            _, ax = pitch.draw()

            def get_color(player):
                if player.team == pass_event.player.team:
                    return "#b94b75"
                else:
                    return "#7f63b8"

            x, y, color = zip(
                *[
                    (coordinates.x, coordinates.y, get_color(player))
                    for player, coordinates in pass_event.freeze_frame.players_coordinates.items()
                ]
            )

            # plot the players
            _ = pitch.scatter(x, y, color=color, s=100, ax=ax)

            # plot the pass
            _ = pitch.scatter(
                pass_event.coordinates.x,
                pass_event.coordinates.y,
                marker="football",
                s=200,
                ax=ax,
                zorder=1.2,
            )
            _ = pitch.lines(
                pass_event.coordinates.x,
                pass_event.coordinates.y,
                pass_event.receiver_coordinates.x,
                pass_event.receiver_coordinates.y,
                comet=True,
                label="shot",
                color="#cb5a4c",
                ax=ax,
            )

            # plot the visible area
            visible_area = iter(visible_area)
            visible_area = list(zip(visible_area, visible_area))
            pitch.polygon([visible_area], color=(1, 0, 0, 0.1), ax=ax)

            plt.savefig(
                base_dir / "outputs" / "test_statsbomb_freeze_frame_360.png"
            )

    def test_correct_normalized_deserialization(self):
        """Test if the normalized deserialization is correct"""
        dataset = statsbomb.load(
            event_data=f"{API_URL}/events/3794687.json",
            lineup_data=f"{API_URL}/lineups/3794687.json",
            three_sixty_data=f"{API_URL}/three-sixty/3794687.json",
        )

        # The events should have standardized coordinates
        kickoff = dataset.get_event_by_id(
            "8022c113-e349-4b0b-b4a7-a3bb662535f8"
        )
        assert kickoff.coordinates.x == pytest.approx(0.5, abs=1e-2)
        assert kickoff.coordinates.y == pytest.approx(0.5, abs=1e-2)

        # The shot freeze-frame should have standardized coordinates
        shot_event = dataset.get_event_by_id(
            "a5c60797-631e-418a-9f24-1e9779cb2b42"
        )
        freeze_frame = shot_event.freeze_frame
        player_3089 = dataset.metadata.teams[0].get_player_by_id("3089")
        assert freeze_frame.players_coordinates[
            player_3089
        ].x == pytest.approx(0.762, abs=1e-2)
        assert freeze_frame.players_coordinates[
            player_3089
        ].y == pytest.approx(0.352, abs=1e-2)

        # The 360 freeze-frame should have standardized coordinates
        pass_event = dataset.get_event_by_id(
            "8022c113-e349-4b0b-b4a7-a3bb662535f8"
        )
        coordinates_per_team = defaultdict(list)
        for (
            player,
            coordinates,
        ) in pass_event.freeze_frame.players_coordinates.items():
            coordinates_per_team[player.team.name].append(coordinates)
        print(coordinates_per_team)
        assert coordinates_per_team == {
            "Belgium": [
                Point(x=0.29992169834015553, y=0.5208156671179599),
                Point(x=0.30643713954672475, y=0.7026264079766127),
                Point(x=0.3214467545271119, y=0.3826089652330575),
                Point(x=0.405612967947393, y=0.9422736509345233),
                Point(x=0.4062973621807315, y=0.0482915505598324),
                Point(x=0.42465606231382946, y=0.5964959025774841),
                Point(x=0.4508398556294095, y=0.5289610882963541),
                Point(x=0.4890186975946768, y=0.2568344237508965),
                Point(x=0.4950593030298559, y=0.7029586200529815),
                Point(x=0.4995833333333334, y=0.499375),
            ],
            "Portugal": [
                Point(x=0.5007398055585528, y=0.64528577145353),
                Point(x=0.503027413811032, y=0.8161700273569469),
                Point(x=0.5276528464860737, y=0.2579702535077385),
                Point(x=0.5278342018640673, y=0.3780770836091537),
                Point(x=0.5771632092108575, y=0.5977748576718983),
                Point(x=0.6031968709341459, y=0.5636937522375899),
                Point(x=0.661570167297097, y=0.3648423832684863),
                Point(x=0.6653717429879116, y=0.7616501561039648),
                Point(x=0.665577307051358, y=0.5960104748540174),
                Point(x=0.6887022647928279, y=0.4433104586034662),
            ],
        }

        # Note: the visible area is not standardized
        visible_area = pass_event.freeze_frame.other_data["visible_area"]
        assert visible_area[0] == pytest.approx(120.0)


class TestStatsBombPassEvent:
    """Tests related to deserialzing 30/Pass events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all pass events"""
        events = dataset.find_all("pass")
        assert len(events) == 1101

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play pass"""
        pass_event = dataset.get_event_by_id(
            "b96d1a5e-8435-4cb6-8e05-3251278c59ca"
        )
        # A pass should have a result
        assert pass_event.result == PassResult.COMPLETE
        # A pass should have end coordinates
        assert pass_event.receiver_coordinates == Point(86.15, 53.35)
        # A pass should have an end timestamp
        assert pass_event.receive_timestamp == parse_str_ts(
            "00:35:21.533"
        ) + timedelta(seconds=0.634066)
        # A pass should have a receiver
        assert (
            pass_event.receiver_player.name
            == "Cristiano Ronaldo dos Santos Aveiro"
        )
        # A pass should have a body part
        assert (
            pass_event.get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )
        # A pass can have set piece qualifiers
        assert pass_event.get_qualifier_value(SetPieceQualifier) is None
        # A pass can have pass qualifiers
        assert pass_event.get_qualifier_value(PassQualifier) is None

    def test_pass_qualifiers(self, dataset: EventDataset):
        """It should add pass qualifiers"""
        pass_event = dataset.get_event_by_id(
            "7df4f0dc-f620-4256-90be-aaf5ffdadcae"
        )
        assert pass_event.get_qualifier_values(PassQualifier) == [
            PassType.CROSS,
            PassType.HIGH_PASS,
            PassType.LONG_BALL,
        ]

    def test_set_piece(self, dataset: EventDataset):
        """It should add set piece qualifiers to free kick passes"""
        pass_event = dataset.get_event_by_id(
            "8022c113-e349-4b0b-b4a7-a3bb662535f8"
        )
        assert (
            pass_event.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )

    def test_interception(self, dataset: EventDataset):
        """It should split interception passes into two events"""
        interception = dataset.get_event_by_id(
            "interception-928042e2-4f8f-4ec0-a6fb-55621eea10e1"
        )
        assert interception.event_type == EventType.INTERCEPTION
        assert interception.result == InterceptionResult.SUCCESS

    def test_aerial_duel(self, dataset: EventDataset):
        """It should split passes that follow an aerial duel into two events"""
        duel = dataset.get_event_by_id(
            "duel-9e74c5c4-bb0c-44b5-9722-24e823e376a3"
        )
        assert duel.event_type == EventType.DUEL
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.LOOSE_BALL,
            DuelType.AERIAL,
        ]
        assert duel.result == DuelResult.WON


class TestStatsBombShotEvent:
    """Tests related to deserialzing 16/Shot events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all shot events"""
        events = dataset.find_all("shot")
        assert len(events) == 29

    def test_open_play(self, dataset: EventDataset):
        """Verify specific attributes of simple open play shot"""
        shot = dataset.get_event_by_id("221ce1cb-d70e-47aa-8d7e-c427a1c952ba")
        # A shot event should have a result
        assert shot.result == ShotResult.OFF_TARGET
        # A shot event should have end coordinates
        assert shot.result_coordinates == Point3D(119.95, 48.35, 0.45)
        # A shot event should have a body part
        assert (
            shot.get_qualifier_value(BodyPartQualifier) == BodyPart.LEFT_FOOT
        )
        # An open play shot should not have a set piece qualifier
        assert shot.get_qualifier_value(SetPieceQualifier) is None

    def test_free_kick(self, dataset: EventDataset):
        """It should add set piece qualifiers to free kick shots"""
        shot = dataset.get_event_by_id("7c10ac89-738c-4e99-8c0c-f55bc5c0995e")
        assert (
            shot.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.FREE_KICK
        )

    def test_aerial_duel(self, dataset: EventDataset):
        """It should split shots that follow an aerial duel into two events"""
        duel = dataset.get_event_by_id(
            "duel-cac8f0f3-015a-43d5-b201-0b9997aea3fb"
        )
        assert duel.event_type == EventType.DUEL
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.LOOSE_BALL,
            DuelType.AERIAL,
        ]
        assert duel.result == DuelResult.WON


class TestStatsBombInterceptionEvent:
    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all interception events"""
        events = dataset.find_all("interception")
        assert len(events) == 25 + 9  # interceptions + pass interceptions

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of interceptions"""
        interception = dataset.get_event_by_id(
            "ca963cd5-93cc-4659-887d-29064cf2156d"
        )
        assert interception.result == InterceptionResult.LOST
        assert interception.get_qualifier_value(BodyPartQualifier) is None


class TestStatsBombOwnGoalEvent:
    """Tests related to deserializing 20/Own Goal Against and 25/Own Goal For events"""

    def test_own_goal(self, base_dir: Path):
        """Test own goal events.

        The StatsBomb "Own Goal For" (id = 25) and one "Own Goal Against" (id = 20) events
        should be converted to a single shot event with ShotResult.OWN_GOAL.
        """
        dataset = statsbomb.load(
            lineup_data=base_dir / "files" / "statsbomb_lineup.json",
            event_data=base_dir / "files" / "statsbomb_event.json",
        )

        # The Own Goal For event should be removed
        own_goal_for_event = dataset.get_event_by_id(
            "f942c5b5-df4b-4ee4-9e90-ed5f5"
        )
        assert own_goal_for_event is None

        # The Own Goal Against event should be converted to a shot event
        own_goal_against_event = dataset.get_event_by_id(
            "89dd4f4b-0a70-48d8-a0e7-ac4c"
        )
        assert own_goal_against_event is not None
        assert own_goal_against_event.event_type == EventType.SHOT
        assert own_goal_against_event.result == ShotResult.OWN_GOAL


class TestStatsBombClearanceEvent:
    """Tests related to deserializing 9/Clearance events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all clearance events"""
        events = dataset.find_all("clearance")
        assert len(events) == 35 + 1  # clearances + keeper sweeper

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of clearances"""
        clearance = dataset.get_event_by_id(
            "1c1d8523-d887-4ade-a698-3274b9b0943c"
        )
        # A clearance has no result
        assert clearance.result is None
        # A clearance should have a bodypart (if data version >= 1.1)
        assert (
            clearance.get_qualifier_value(BodyPartQualifier) == BodyPart.HEAD
        )

    def test_aerial_duel(self, dataset: EventDataset):
        """It should split clearances that follow an aerial duel into two events"""
        duel = dataset.get_event_by_id(
            "duel-9bbdb8ea-1119-4d82-bb0d-a63802558fc6"
        )
        assert duel.event_type == EventType.DUEL
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.LOOSE_BALL,
            DuelType.AERIAL,
        ]
        assert duel.result == DuelResult.WON


class TestStatsBombMiscontrolEvent:
    """Tests related to deserializing 19/Miscontrol events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all miscontrol events"""
        events = dataset.find_all("miscontrol")
        assert len(events) == 22

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of miscontrols"""
        miscontrol = dataset.get_event_by_id(
            "e297def3-9907-414a-9eb5-e1269343b84d"
        )
        # A miscontrol has no result
        assert miscontrol.result is None
        # A miscontrol has no qualifiers
        assert miscontrol.qualifiers is None

    def test_aerial_duel(self, dataset: EventDataset):
        """It should split clearances that follow an aerial duel into two events"""
        assert True  # can happen according to the documentation, but not in the dataset


class TestStatsBombDribbleEvent:
    """Tests related to deserializing 17/Dribble events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all dribble events"""
        events = dataset.find_all("take_on")
        assert len(events) == 33

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of dribbles"""
        dribble = dataset.get_event_by_id(
            "82dae1ed-7944-4064-b409-6652dd4a2e72"
        )
        # A dribble should have a result
        assert dribble.result == TakeOnResult.INCOMPLETE
        # A dribble has no qualifiers
        assert dribble.qualifiers is None

    def test_result_out(self, dataset: EventDataset):
        """The result of a dribble can be TakeOnResult.OUT"""
        dribble = dataset.get_event_by_id(
            "e5dfa799-1dc7-49c1-94b8-ee793ae6284b"
        )
        assert dribble.result == TakeOnResult.OUT


class TestStatsBombCarryEvent:
    """Tests related to deserializing 22/Carry events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all carry events"""
        events = dataset.find_all("carry")
        assert len(events) == 929

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of carries"""
        carry = dataset.get_event_by_id("fab6360a-cbc2-45a3-aafa-5f3ec81eb9c7")
        # A carry is always successful
        assert carry.result == CarryResult.COMPLETE
        # A carry has no qualifiers
        assert carry.qualifiers is None
        # A carry should have an end location
        assert carry.end_coordinates == Point(21.65, 54.85)
        # A carry should have an end timestamp
        assert carry.end_timestamp == parse_str_ts("00:20:11.457") + timedelta(
            seconds=1.365676
        )


class TestStatsBombDuelEvent:
    """Tests related to deserializing 1/Duel events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all duel and 50/50 events"""
        events = dataset.find_all("duel")
        assert (
            len(events) == 59 + 4 + 26
        )  # duels + 50/50 + aerial won attribute

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of duels"""
        duel = dataset.get_event_by_id("15c4bfaa-36fd-4b3e-bec1-bc8bcc1febb9")
        # A duel should have a result
        assert duel.result == DuelResult.WON
        # A duel should have a duel type
        assert duel.get_qualifier_values(DuelQualifier) == [DuelType.GROUND]
        # A duel does not have a body part
        assert duel.get_qualifier_value(BodyPartQualifier) is None

    def test_aerial_duel_qualfiers(self, dataset: EventDataset):
        """It should add aerial duel + loose ball qualifiers"""
        duel = dataset.get_event_by_id("f0a98e60-10e8-49a7-b778-6dc640ee9581")
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.LOOSE_BALL,
            DuelType.AERIAL,
        ]

    def test_tackle_qualfiers(self, dataset: EventDataset):
        """It should add ground duel qualifiers"""
        duel = dataset.get_event_by_id("15c4bfaa-36fd-4b3e-bec1-bc8bcc1febb9")
        assert duel.get_qualifier_values(DuelQualifier) == [DuelType.GROUND]

    def test_loose_ground_duel_qualfiers(self, dataset: EventDataset):
        """It should add ground duel + loose ball qualifiers"""
        duel = dataset.get_event_by_id("767e21ed-ef76-4d96-b6a8-131c3ee27ed0")
        assert duel.get_qualifier_values(DuelQualifier) == [
            DuelType.LOOSE_BALL,
            DuelType.GROUND,
        ]


class TestStatsBombGoalkeeperEvent:
    """Tests related to deserializing 30/Goalkeeper events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all goalkeeper events"""
        events = dataset.find_all("goalkeeper")
        assert (
            len(events) == 32 - 24 - 1 - 1
        )  # goalkeeper events - shot faced - goal conceded - clearance

    def test_save(self, dataset: EventDataset):
        """It should deserialaize goalkeeper saves"""
        # A save should be deserialized as a goalkeeper event
        save = dataset.get_event_by_id("c8e313fb-8ac0-41af-87dc-4a94afcaee4f")
        assert save.get_qualifier_value(GoalkeeperQualifier) == (
            GoalkeeperActionType.SAVE
        )
        # A save attempt should not be deserialized as a goalkeeper event
        goal_conceded = dataset.get_event_by_id(
            "3eb5f3a7-3654-4c85-8880-3ecc741dbb57"
        )
        assert goal_conceded.event_type == EventType.GENERIC
        shot_faced = dataset.get_event_by_id(
            "f60ea856-c679-4d1e-aa0c-5ce1a47a1353"
        )
        assert shot_faced.event_type == EventType.GENERIC

    def test_punch(self, dataset: EventDataset):
        """It should deserialize goalkeeper punches"""
        assert True  # no example in the dataset

    def test_smother(self, dataset: EventDataset):
        """It should deserialize goalkeeper smothers"""
        assert True  # no example in the dataset

    def test_collected(self, dataset: EventDataset):
        """It should deserialize goalkeeper collections"""
        collected = dataset.get_event_by_id(
            "5156545b-7add-4b6a-a8e4-c68672267464"
        )
        assert collected.get_qualifier_value(GoalkeeperQualifier) == (
            GoalkeeperActionType.CLAIM
        )

    def test_keeper_sweeper(self, dataset: EventDataset):
        """It should deserialize keeper sweeper actions"""
        # keeper sweeper with outcome 'clear' should be deserialized as
        # as a clearance event if the keeper uses his feet or head
        sweeper_clear = dataset.get_event_by_id(
            "6c84a193-d45b-4d6e-97bc-3f07af9001db"
        )
        assert sweeper_clear.event_type == EventType.CLEARANCE
        # keeper sweeper with outcome 'claim' should be deserialized as
        # a goalkeeper pick-up event if the keeper uses his hands
        sweeper_claim = dataset.get_event_by_id(
            "460f558e-c951-4262-b467-e078ea1faefc"
        )
        assert sweeper_claim.get_qualifier_value(GoalkeeperQualifier) == (
            GoalkeeperActionType.PICK_UP
        )


class TestStatsBombSubstitutionEvent:
    """Tests related to deserializing 18/Substitution events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all substitution events"""
        events = dataset.find_all("substitution")
        assert len(events) == 8

        # Verify that the player and replacement player are set correctly
        subs = [
            (3089, 5630),
            (3168, 12041),
            (3193, 5204),
            (9929, 5218),
            (12169, 13621),
            (3593, 11173),
            (3621, 5633),
            (5632, 6331),
        ]
        for event_idx, (player_id, replacement_player_id) in enumerate(subs):
            event = cast(SubstitutionEvent, events[event_idx])
            assert event.player == event.team.get_player_by_id(player_id)
            assert event.replacement_player == event.team.get_player_by_id(
                replacement_player_id
            )


class TestsStatsBombBadBehaviourEvent:
    """Tests related to deserializing 22/Bad Behaviour events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should create a card event for each card given"""
        events = dataset.find_all("card")
        assert len(events) == 3 + 2  # bad behaviour + foul with card

        for event in events:
            assert event.card_type == CardType.FIRST_YELLOW

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of cards"""
        card = dataset.get_event_by_id("a661cfcc-a5d3-4156-9a22-4842caf2c071")
        # A card should have a card type
        assert card.card_type == CardType.FIRST_YELLOW
        # Card qualifiers should not be added
        assert card.get_qualifier_value(CardQualifier) is None


class TestStatsBombFoulCommittedEvent:
    """Tests related to deserializing 2/Foul Committed events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all foul committed events"""
        events = dataset.find_all("foul_committed")
        assert len(events) == 27

    def test_card(self, dataset: EventDataset):
        """It should add a card qualifier if a card was given"""
        foul_with_card = dataset.get_event_by_id(
            "5c3421f8-17c1-4a84-8fd2-1dbd11724156"
        )
        assert (
            foul_with_card.get_qualifier_value(CardQualifier)
            == CardType.FIRST_YELLOW
        )

        foul_without_card = dataset.get_event_by_id(
            "309c22be-d1fc-43a4-a9ee-4643c04afb14"
        )
        assert foul_without_card.get_qualifier_value(CardQualifier) is None


class TestStatsBombPlayerOffEvent:
    """Tests related to deserializing 19/Player Off events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all player off events"""
        events = dataset.find_all("player_off")
        assert len(events) == 0


class TestStatsBombPlayerOnEvent:
    """Tests related to deserializing 20/Player On events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all player on events"""
        events = dataset.find_all("player_on")
        assert len(events) == 0


class TestStatsBombRecoveryEvent:
    """Tests related to deserializing 23/Recovery events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all ball recovery events"""
        events = dataset.find_all("recovery")
        assert len(events) == 97


class TestStatsBombTacticalShiftEvent:
    """Tests related to deserializing 34/Tactical Shift events"""

    def test_deserialize_all(self, dataset: EventDataset):
        """It should deserialize all tactical shift events"""
        events = dataset.find_all("formation_change")
        assert len(events) == 2

    def test_attributes(self, dataset: EventDataset):
        """Verify specific attributes of tactical shift events"""
        formation_change = dataset.get_event_by_id(
            "983cdd00-6f7f-4d62-bfc2-74e4e5b0137f"
        )
        assert formation_change.formation_type == FormationType("4-3-3")
