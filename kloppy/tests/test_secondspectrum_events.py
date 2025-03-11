import pytest
from pathlib import Path
from unittest.mock import MagicMock

from kloppy.domain.models import EventDataset
from kloppy.domain import (
    Provider,
    PassEvent,
    PassResult,
    ShotEvent,
    ShotResult,
    DuelEvent,
    DuelResult,
    SetPieceType,
)
from kloppy.domain.models.event import (
    BodyPartQualifier,
    BodyPart,
    GoalkeeperQualifier,
    GoalkeeperActionType,
    DeflectionEvent,
    DeflectionResult,
    CardEvent,
    CardType,
    FoulCommittedEvent,
    BallOutEvent,
    ClearanceEvent,
    SubstitutionEvent,
    TakeOnEvent,
)


from kloppy import secondspectrum


from kloppy.domain.models.event import EventType


class TestSecondSpectrumEvents:
    @pytest.fixture
    def meta_data(self, base_dir) -> Path:
        return base_dir / "files/secondspectrum_fake_metadata.json"

    @pytest.fixture
    def event_data_file(self, base_dir) -> Path:
        return base_dir / "files/secondspectrum_fake_eventdata.jsonl"

    @pytest.fixture
    def dataset(self, meta_data: Path, event_data_file: Path) -> EventDataset:
        return secondspectrum.load_event_data(
            meta_data=meta_data, event_data=event_data_file
        )

    def test_deserialize_pass_event(
        self,
        meta_data: Path,
        event_data_file: Path,
        dataset: EventDataset,
    ):

        assert isinstance(dataset, EventDataset)
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM

        pass_events = [
            event for event in dataset.records if isinstance(event, PassEvent)
        ]
        assert len(pass_events) > 0
        assert pass_events[0].result in [
            PassResult.COMPLETE,
            PassResult.INCOMPLETE,
        ]

    def test_deserialize_shot_event(
        self,
        meta_data: Path,
        event_data_file: Path,
        dataset: EventDataset,
    ):

        assert isinstance(dataset, EventDataset)
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM

        shot_events = [
            event for event in dataset.records if isinstance(event, ShotEvent)
        ]
        assert len(shot_events) > 0

        shot_event = shot_events[0]
        assert (
            shot_event.result == ShotResult.GOAL
            or shot_event.result == ShotResult.SAVED
            or shot_event.result == ShotResult.OFF_TARGET
            or shot_event.result == ShotResult.BLOCKED
        )

    # def test_deserialize_duel_event(self,
    #     meta_data: Path,
    #     event_data_file: Path,
    #             dataset: EventDataset,

    # ):

    #         assert isinstance(dataset, EventDataset)
    #         assert dataset.metadata.provider == Provider.SECONDSPECTRUM

    #         duel_events = [
    #             event
    #             for event in dataset.records
    #             if isinstance(event, DuelEvent)
    #         ]
    #         assert len(duel_events) > 0

    #         duel_event = duel_events[0]
    #         assert (
    #             duel_event.result == DuelResult.WON
    #             or duel_event.result == DuelResult.LOST
    #             or duel_event.result == DuelResult.NEUTRAL
    #         )

    def test_deserialize_deflection_event(
        self,
        meta_data: Path,
        event_data_file: Path,
        dataset: EventDataset,
    ):

        assert isinstance(dataset, EventDataset)
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM

        deflection_events = [
            event
            for event in dataset.records
            if isinstance(event, DeflectionEvent)
        ]
        assert len(deflection_events) > 0

        deflection_event = deflection_events[0]
        assert (
            deflection_event.result == DeflectionResult.SUCCESS
            or deflection_event.result == DeflectionResult.FAILED
        )

    # def test_deserialize_card_event(self,
    #     meta_data: Path,
    #     event_data_file: Path,
    #             dataset: EventDataset,

    # ):

    #         assert isinstance(dataset, EventDataset)
    #         assert dataset.metadata.provider == Provider.SECONDSPECTRUM

    #         card_events = [
    #             event
    #             for event in dataset.records
    #             if isinstance(event, CardEvent)
    #         ]
    #         assert len(card_events) > 0

    #         card_event = card_events[0]
    #         assert card_event.card_type in [
    #             CardType.FIRST_YELLOW,
    #             CardType.SECOND_YELLOW,
    #             CardType.RED,
    #         ]

    def test_deserialize_foul_event(
        self,
        meta_data: Path,
        event_data_file: Path,
        dataset: EventDataset,
    ):

        assert isinstance(dataset, EventDataset)
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM

        foul_events = [
            event
            for event in dataset.records
            if isinstance(event, FoulCommittedEvent)
        ]
        assert len(foul_events) > 0

    def test_deserialize_ball_out_event(
        self,
        dataset: EventDataset,
    ):

        assert isinstance(dataset, EventDataset)
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM

        ball_out_events = [
            event
            for event in dataset.records
            if isinstance(event, BallOutEvent)
        ]
        assert len(ball_out_events) > 0

        ball_out_event = ball_out_events[0]
        assert ball_out_event.event_name is not None

    def test_deserialize_clearance_event(
        self,
        dataset: EventDataset,
    ):

        assert isinstance(dataset, EventDataset)
        assert dataset.metadata.provider == Provider.SECONDSPECTRUM

        clearance_events = [
            event
            for event in dataset.records
            if isinstance(event, ClearanceEvent)
        ]
        assert len(clearance_events) > 0

        clearance_event = clearance_events[0]
        assert clearance_event.event_name is not None


#     def test_deserialize_substitution_event(self, meta_data: Path, event_data_file: Path,        dataset: EventDataset,
# ):
#         """Test for correct deserialization of substitution events"""


#         assert isinstance(dataset, EventDataset)
#         assert dataset.metadata.provider == Provider.SECONDSPECTRUM

#         substitution_events = [
#             event
#             for event in dataset.records
#             if isinstance(event, SubstitutionEvent)
#         ]
#         assert len(substitution_events) > 0

#         substitution_event = substitution_events[0]
#         assert substitution_event.player_out is not None
#         assert substitution_event.replacement_player is not None
#         # Check if the team attribute is set
#         assert substitution_event.team_id is not None

#     def test_deserialize_take_on_event(self, meta_data: Path, event_data_file: Path,        dataset: EventDataset,
# ):
#         """Test for correct deserialization of take-on events"""

#         assert isinstance(dataset, EventDataset)
#         assert dataset.metadata.provider == Provider.SECONDSPECTRUM

#         take_on_events = [
#             event
#             for event in dataset.records
#             if isinstance(event, TakeOnEvent)
#         ]
#         assert len(take_on_events) > 0

#         take_on_event = take_on_events[0]
#         assert take_on_event.result is not None
#         assert take_on_event.player_id is not None
#         assert take_on_event.position is not None
#         assert take_on_event.team_id is not None
