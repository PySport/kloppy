from collections import defaultdict
from pathlib import Path

import pytest

from kloppy.domain import (
    AttackingDirection,
    BodyPart,
    BodyPartQualifier,
    DatasetType,
    DuelQualifier,
    DuelType,
    Orientation,
    Period,
    Point,
    Provider,
    FormationType,
    Frame,
    Position,
)

from kloppy import statsbomb
from kloppy.domain.models.event import (
    CardType,
    PassQualifier,
    PassType,
    EventType,
)


class TestStatsBomb:
    """"""

    @pytest.fixture
    def event_data(self, base_dir) -> str:
        return base_dir / "files/statsbomb_event.json"

    @pytest.fixture
    def lineup_data(self, base_dir) -> str:
        return base_dir / "files/statsbomb_lineup.json"

    def test_correct_deserialization(
        self, lineup_data: Path, event_data: Path
    ):
        """
        This test uses data from the StatsBomb open data project.
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            coordinates="statsbomb",
        )

        assert dataset.metadata.provider == Provider.STATSBOMB
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 4039
        assert len(dataset.metadata.periods) == 2
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        assert dataset.metadata.teams[0].name == "Barcelona"
        assert dataset.metadata.teams[1].name == "Deportivo Alavés"
        assert dataset.metadata.teams[0].starting_formation == FormationType(
            "4-4-2"
        )
        assert dataset.metadata.teams[1].starting_formation == FormationType(
            "4-1-4-1"
        )

        player = dataset.metadata.teams[0].get_player_by_id("5503")
        assert player.player_id == "5503"
        assert player.jersey_no == 10
        assert str(player) == "Lionel Andrés Messi Cuccittini"
        assert player.position == Position(
            position_id="24", name="Left Center Forward", coordinates=None
        )
        assert player.starting

        sub_player = dataset.metadata.teams[0].get_player_by_id("3501")
        assert str(sub_player) == "Philippe Coutinho Correia"
        assert not sub_player.starting

        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=0.0,
            end_timestamp=2705.267,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=2705.268,
            end_timestamp=5557.321,
            attacking_direction=AttackingDirection.NOT_SET,
        )

        assert dataset.events[10].coordinates == Point(34.5, 20.5)

        assert (
            dataset.events[794].get_qualifier_value(BodyPartQualifier)
            == BodyPart.HEAD
        )

        assert (
            dataset.events[2232].get_qualifier_value(BodyPartQualifier)
            == BodyPart.RIGHT_FOOT
        )

        assert (
            dataset.events[195].get_qualifier_value(BodyPartQualifier) is None
        )

        assert (
            dataset.events[1438].get_qualifier_value(PassQualifier)
            == PassType.CROSS
        )

        assert (
            dataset.events[1557].get_qualifier_value(PassQualifier)
            == PassType.THROUGH_BALL
        )

        assert (
            dataset.events[444].get_qualifier_value(PassQualifier)
            == PassType.SWITCH_OF_PLAY
        )

        assert (
            dataset.events[101].get_qualifier_value(PassQualifier)
            == PassType.LONG_BALL
        )

        assert (
            dataset.events[17].get_qualifier_value(PassQualifier)
            == PassType.HIGH_PASS
        )

        assert (
            dataset.events[654].get_qualifier_value(PassQualifier)
            == PassType.HEAD_PASS
        )

        assert (
            dataset.events[3145].get_qualifier_value(PassQualifier)
            == PassType.HAND_PASS
        )

        assert (
            dataset.events[3622].get_qualifier_value(PassQualifier)
            == PassType.ASSIST
        )

        assert dataset.events[3400].get_qualifier_value(PassQualifier) is None

        assert (
            dataset.events[194].get_qualifier_values(DuelQualifier)[1].value
            == DuelType.AERIAL
        )
        assert (
            dataset.events[4032].get_qualifier_values(DuelQualifier)[1].value
            == DuelType.GROUND
        )
        assert dataset.events[272].event_type == EventType.CLEARANCE

    def test_correct_normalized_deserialization(
        self, lineup_data: Path, event_data: Path
    ):
        """
        This test uses data from the StatsBomb open data project.
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data, event_data=event_data
        )

        assert dataset.events[10].coordinates == Point(0.2875, 0.25625)

    def test_substitution(self, lineup_data: Path, event_data: Path):
        """
        Test substitution events
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            event_types=["substitution"],
        )

        assert len(dataset.events) == 6

        subs = [
            (6374, 3501),
            (6839, 6935),
            (6581, 6566),
            (6613, 6624),
            (5477, 11392),
            (5203, 8206),
        ]

        for event_idx, (player_id, replacement_player_id) in enumerate(subs):
            event = dataset.events[event_idx]
            assert event.player == event.team.get_player_by_id(player_id)
            assert event.replacement_player == event.team.get_player_by_id(
                replacement_player_id
            )

    def test_card(self, lineup_data: Path, event_data: Path):
        """
        Test card events
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            event_types=["card"],
        )

        assert len(dataset.events) == 2

        for card in dataset.events:
            assert card.card_type == CardType.FIRST_YELLOW

    def test_foul_committed(self, lineup_data: Path, event_data: Path):
        """
        Test foul committed events
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            event_types=["foul_committed"],
        )

        assert len(dataset.events) == 23

    def test_related_events(self, lineup_data: Path, event_data: Path):
        dataset = statsbomb.load(
            lineup_data=lineup_data, event_data=event_data
        )
        carry_event = dataset.get_event_by_id(
            "8e3dacc2-7a39-4301-9053-e78cfec1aa95"
        )
        pass_event = dataset.get_event_by_id(
            "d1cccb73-c7ef-4b02-8267-ebd7f149904b"
        )
        receipt_event = dataset.get_event_by_id(
            "61da36dc-d862-416c-8ee3-1a0cd24dc086"
        )

        assert carry_event.get_related_events() == [receipt_event, pass_event]
        assert carry_event.related_pass() == pass_event

    def test_player_position(self, lineup_data: Path, event_data: Path):
        """
        Validate position information is loaded correctly from the STARTING_XI events.

        TODO: Fix when player is substituted
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
        )
        player_5246 = dataset.metadata.teams[0].get_player_by_id(20055)
        assert player_5246.position.position_id == "1"

    def test_freeze_frame(self, lineup_data: Path, event_data: Path):
        """
        Test freeze-frame is properly loaded and attached to shot events. The
        freeze-frames contain location information on player level.
        """
        dataset = statsbomb.load(
            lineup_data=lineup_data,
            event_data=event_data,
            coordinates="statsbomb",
        )
        shot_event = dataset.get_event_by_id(
            "65f16e50-7c5d-4293-b2fc-d20887a772f9"
        )

        event_player_coordinates = shot_event.freeze_frame.players_coordinates[
            shot_event.player
        ]
        assert event_player_coordinates == shot_event.coordinates

        player_5246 = dataset.metadata.teams[0].get_player_by_id(5246)
        assert shot_event.freeze_frame.players_coordinates[
            player_5246
        ] == Point(103.2, 43.6)

        assert shot_event.freeze_frame.frame_id == 3727

    def test_freeze_frame_360(self, base_dir):
        dataset = statsbomb.load(
            event_data=base_dir / "files/statsbomb_3788741_event.json",
            lineup_data=base_dir / "files/statsbomb_3788741_lineup.json",
            three_sixty_data=base_dir / "files/statsbomb_3788741_360.json",
            coordinates="statsbomb",
        )

        pass_event = dataset.find("pass")
        coordinates_per_team = defaultdict(list)
        for (
            player,
            coordinates,
        ) in pass_event.freeze_frame.players_coordinates.items():
            coordinates_per_team[player.team.name].append(coordinates)

        assert coordinates_per_team == {
            "Italy": [
                Point(x=43.672042000000005, y=31.609489),
                Point(x=44.016185, y=45.22054),
                Point(x=49.69454, y=35.055324000000006),
                Point(x=54.51254, y=29.714278),
                Point(x=58.29811, y=48.149497000000004),
                Point(x=60.362968, y=30.403444999999998),
            ],
            "Turkey": [
                Point(x=60.018825, y=39.621055000000005),
                Point(x=61.223323, y=47.977206),
                Point(x=67.417896, y=32.643237000000006),
                Point(x=68.96654000000001, y=43.325328000000006),
            ],
        }

        assert pass_event.freeze_frame.players_coordinates[
            pass_event.player
        ] == Point(x=60.018825, y=39.621055000000005)

        assert pass_event.freeze_frame.frame_id == 21
