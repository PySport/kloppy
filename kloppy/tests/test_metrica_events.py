import copy
from datetime import timedelta
import json
from pathlib import Path

import pytest

from kloppy import metrica
from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    CardType,
    EventDataset,
    EventType,
    InterceptionResult,
    Orientation,
    PassResult,
    Point,
    Provider,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
)
from kloppy.domain.models.common import DatasetType


class TestMetricaEvents:
    """Tests related to deserialization of Metrica JSON events."""

    @pytest.fixture(scope="class")
    def dataset(self, base_dir: Path) -> EventDataset:
        """Load a Metrica event dataset."""
        dataset = metrica.load_event(
            # FIXME: these files represent different matches
            event_data=base_dir / "files" / "metrica_events.json",
            meta_data=base_dir / "files" / "epts_metrica_metadata.xml",
        )
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 3594
        return dataset

    @pytest.fixture(scope="class")
    def raw_events(self, base_dir: Path) -> dict[int, dict]:
        """The raw Metrica events, keyed by their index."""
        with open(base_dir / "files" / "metrica_events.json") as f:
            return {event["index"]: event for event in json.load(f)["data"]}

    @pytest.fixture
    def load_events(self, base_dir: Path, tmp_path: Path):
        """Load a dataset from a custom list of raw Metrica events.

        This is used to test event types that do not occur in the sample data.
        """

        def _load(events: list[dict]) -> EventDataset:
            event_data = tmp_path / "events.json"
            event_data.write_text(json.dumps({"data": events}))
            return metrica.load_event(
                event_data=event_data,
                meta_data=base_dir / "files" / "epts_metrica_metadata.xml",
            )

        return _load

    def test_metadata(self, dataset: EventDataset):
        """It should parse the metadata correctly."""
        assert dataset.metadata.provider == Provider.METRICA
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation is Orientation.HOME_AWAY
        assert dataset.metadata.teams[0].name == "Team A"
        assert dataset.metadata.teams[1].name == "Team B"
        player = dataset.metadata.teams[0].players[10]
        assert player.player_id == "Track_11"
        assert player.jersey_no == 11
        assert str(player) == "Track_11"
        assert player.starting_position.name == "Goalkeeper"

        assert dataset.metadata.periods[0].id == 1
        assert dataset.metadata.periods[0].start_timestamp == timedelta(
            seconds=18
        )
        assert dataset.metadata.periods[0].end_timestamp == timedelta(
            seconds=19.96
        )
        assert dataset.metadata.periods[1].id == 2
        assert dataset.metadata.periods[1].start_timestamp == timedelta(
            seconds=26
        )
        assert dataset.metadata.periods[1].end_timestamp == timedelta(
            seconds=27.96
        )

    def test_timestamps(self, dataset: EventDataset):
        """It should parse the timestamps correctly."""
        # note: these timestamps are odd because the metadata and event data
        # are from different matches
        assert dataset.events[0].timestamp == timedelta(
            seconds=14.44
        ) - timedelta(seconds=450 / 25)  # kickoff first half
        assert dataset.events[1749].timestamp == timedelta(
            seconds=2803.6
        ) - timedelta(seconds=650 / 25)  # kickoff second half

    def test_coordinates(self, dataset: EventDataset):
        """It should parse the coordinates of events correctly."""
        assert dataset.events[0].coordinates == Point(x=0.50125, y=0.48725)

    def test_body_part_qualifiers(self, dataset: EventDataset):
        """It should add body part qualifiers to the event."""
        # The body part qualifier should be set for headers
        header = dataset.get_event_by_id("99")
        assert header.get_qualifier_value(BodyPartQualifier) == BodyPart.HEAD
        # It should be None (i.e., unknown) for events that are not headers
        foot = dataset.get_event_by_id("2")
        assert foot.get_qualifier_value(BodyPartQualifier) is None

    def test_set_piece(self, dataset: EventDataset):
        """It should integrate set piece events in the next event."""
        # The next event can be a pass
        kick_off_event = dataset.get_event_by_id("1")
        assert kick_off_event is None
        pass_after_kick_off = dataset.get_event_by_id("2")
        assert (
            pass_after_kick_off.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )
        # or a shot
        free_kick_event = dataset.get_event_by_id("130")
        assert free_kick_event is None
        shot_after_free_kick = dataset.get_event_by_id("131")
        assert (
            shot_after_free_kick.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.FREE_KICK
        )

    def test_clearance(self, dataset: EventDataset):
        """It should deserialize events with the CLEARANCE subtype as clearances."""
        clearances = dataset.find_all("clearance")
        # 11 BALL LOST and 11 BALL OUT events have the CLEARANCE subtype
        assert len(clearances) == 22
        assert all(clearance.result is None for clearance in clearances)

        # A clearance that does not go out of bounds (BALL LOST)
        clearance = dataset.get_event_by_id("142")
        assert clearance.event_type == EventType.CLEARANCE
        assert clearance.next().event_type != EventType.BALL_OUT

        # A clearance that goes out of bounds (BALL OUT) is followed by
        # a synthetic ball out event at the end location of the clearance
        clearance_out = dataset.get_event_by_id("588")
        assert clearance_out.event_type == EventType.CLEARANCE
        ball_out = clearance_out.next()
        assert ball_out.event_type == EventType.BALL_OUT
        assert ball_out.coordinates == Point(x=-0.02, y=0.86)

        # It should keep the body part qualifier
        header = dataset.get_event_by_id("597")
        assert header.event_type == EventType.CLEARANCE
        assert header.get_qualifier_value(BodyPartQualifier) == BodyPart.HEAD

    def test_clearance_from_pass(self, raw_events: dict, load_events):
        """It should deserialize a PASS with the CLEARANCE subtype as a clearance.

        The sample data has no such event, so one is created by adding the
        CLEARANCE subtype to the pass that follows the kick-off.
        """
        kick_off, kick_off_pass = copy.deepcopy([raw_events[1], raw_events[2]])
        kick_off_pass["subtypes"] = {"name": "CLEARANCE", "id": 12}

        dataset = load_events([kick_off, kick_off_pass])

        clearance = dataset.get_event_by_id("2")
        assert clearance.event_type == EventType.CLEARANCE
        # set piece qualifiers should not get lost
        assert (
            clearance.get_qualifier_value(SetPieceQualifier)
            == SetPieceType.KICK_OFF
        )

    def test_interception(self, dataset: EventDataset):
        """It should deserialize RECOVERY events with the INTERCEPTION subtype
        as interceptions."""
        interceptions = dataset.find_all("interception")
        assert len(interceptions) == 127

        # The intercepted pass is a BALL LOST event with the INTERCEPTION
        # subtype. It describes how the passer lost the ball, so it should
        # remain an incomplete pass of the team that lost the ball.
        intercepted_pass = dataset.get_event_by_id("66")
        assert intercepted_pass.event_type == EventType.PASS
        assert intercepted_pass.result == PassResult.INCOMPLETE
        assert intercepted_pass.team.team_id == "TEAM_B"

        # The interception is the RECOVERY event of the opponent
        interception = dataset.get_event_by_id("67")
        assert interception.event_type == EventType.INTERCEPTION
        assert interception.team.team_id == "TEAM_A"
        assert interception.ball_owning_team.team_id == "TEAM_A"

        # RECOVERY events without the INTERCEPTION subtype remain recoveries
        assert len(dataset.find_all("recovery")) == 294 - 127

    @pytest.mark.parametrize(
        "event_id, next_event_type, expected_result",
        [
            # followed by a carry of the intercepting player
            ("67", EventType.CARRY, InterceptionResult.SUCCESS),
            # the intercepting player's touch goes to an opponent (BALL LOST)
            ("105", EventType.PASS, InterceptionResult.LOST),
            # the intercepting player's touch goes out of bounds (BALL OUT)
            ("209", EventType.PASS, InterceptionResult.OUT),
        ],
    )
    def test_interception_result(
        self,
        dataset: EventDataset,
        event_id: str,
        next_event_type: EventType,
        expected_result: InterceptionResult,
    ):
        """It should infer the result of an interception from the next
        event of the intercepting player."""
        interception = dataset.get_event_by_id(event_id)
        assert interception.event_type == EventType.INTERCEPTION
        assert interception.next().event_type == next_event_type
        assert interception.result == expected_result

    def test_card(self, dataset: EventDataset):
        """It should deserialize CARD events as cards."""
        cards = dataset.find_all("card")
        assert len(cards) == 1

        yellow_card = dataset.get_event_by_id("2660")
        assert yellow_card.event_type == EventType.CARD
        assert yellow_card.card_type == CardType.FIRST_YELLOW
        assert yellow_card.team.team_id == "TEAM_B"
        assert yellow_card.ball_owning_team is None

    @pytest.mark.parametrize(
        "subtype_name, expected_event_type, expected_card_type",
        [
            ("RED", EventType.CARD, CardType.RED),
            # kloppy has no card type for the dismissal of technical area
            # personnel, so it should remain a generic event
            ("DISMISSAL", EventType.GENERIC, None),
        ],
    )
    def test_card_type(
        self,
        raw_events: dict,
        load_events,
        subtype_name: str,
        expected_event_type: EventType,
        expected_card_type: CardType,
    ):
        """It should parse the card type from the subtype of the CARD event.

        The sample data only contains a yellow card, so the other subtypes
        are created by renaming its subtype. Their ids are not known, so the
        card type is matched on the subtype name.
        """
        card = copy.deepcopy(raw_events[2660])
        card["subtypes"] = {"name": subtype_name, "id": -1}

        dataset = load_events([card])

        event = dataset.get_event_by_id("2660")
        assert event.event_type == expected_event_type
        assert getattr(event, "card_type", None) == expected_card_type

    @pytest.mark.parametrize(
        "subtypes",
        [
            {"name": "GOAL", "id": 30},
            # an own goal from a clearance should not be a clearance
            [{"name": "CLEARANCE", "id": 12}, {"name": "GOAL", "id": 30}],
        ],
    )
    def test_own_goal(self, raw_events: dict, load_events, subtypes):
        """It should deserialize a BALL OUT event with the GOAL subtype as
        an own goal.

        The sample data has no own goal, so one is created from a ball out
        event of a defender close to their own goal.
        """
        previous_event, own_goal = copy.deepcopy(
            [raw_events[587], raw_events[588]]
        )
        own_goal["subtypes"] = subtypes
        own_goal["end"]["y"] = 0.5

        dataset = load_events([previous_event, own_goal])

        shot = dataset.get_event_by_id("588")
        assert shot.event_type == EventType.SHOT
        assert shot.result == ShotResult.OWN_GOAL
        # the team of the player that scored the own goal
        assert shot.team.team_id == "TEAM_B"
        # like for other goals, no synthetic ball out event is added
        assert shot.next() is None
