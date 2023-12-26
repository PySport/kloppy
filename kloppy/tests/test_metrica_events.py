from pathlib import Path
import pytest

from kloppy import metrica
from kloppy.domain import (
    Orientation,
    Period,
    Provider,
    AttackingDirection,
    SetPieceType,
    BodyPart,
    EventDataset,
    Point,
    SetPieceQualifier,
    BodyPartQualifier,
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

    def test_metadata(self, dataset: EventDataset):
        """It should parse the metadata correctly."""
        assert dataset.metadata.provider == Provider.METRICA
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation is Orientation.HOME_TEAM
        assert dataset.metadata.teams[0].name == "Team A"
        assert dataset.metadata.teams[1].name == "Team B"
        player = dataset.metadata.teams[0].players[10]
        assert player.player_id == "Track_11"
        assert player.jersey_no == 11
        assert str(player) == "Track_11"
        assert player.position.name == "Goalkeeper"

        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=14.44,
            end_timestamp=2783.76,
            attacking_direction=AttackingDirection.NOT_SET,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=2803.6,
            end_timestamp=5742.12,
            attacking_direction=AttackingDirection.NOT_SET,
        )

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
