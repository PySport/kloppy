import os

from kloppy import (
    MetricaTrackingSerializer,
    MetricaEventsJsonSerializer,
    load_sportec_event_data,
)
from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    EventType,
)
from kloppy.domain.models.common import DatasetType


class TestSportecEvent:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        dataset = load_sportec_event_data(
            f"{base_dir}/files/sportec_events.xml",
            f"{base_dir}/files/sportec_meta.xml",
        )

        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2

        # raw_event must be flattened dict
        assert isinstance(dataset.events[0].raw_event, dict)

        assert len(dataset.events) == 28
        assert dataset.metadata.orientation == Orientation.FIXED_HOME_AWAY
        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=1591381800.21,
            end_timestamp=1591384584.0,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=1591385607.01,
            end_timestamp=1591388598.0,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "DFL-OBJ-00001D"
        assert player.jersey_no == 1
        assert str(player) == "A. Schwolow"
        assert player.position.position_id is None
        assert player.position.name == "TW"
