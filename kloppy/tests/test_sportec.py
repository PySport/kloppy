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
)
from kloppy.domain.models.common import DatasetType


class TestSportecEvent:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        dataset = load_sportec_event_data(
            "/Users/koen/Dropbox/PySport/kloppy-dev/Eventdata_DFL-MAT-003BN1.xml",
            "/Users/koen/Dropbox/PySport/kloppy-dev/Match_Infos_DFL-MAT-003BN1.xml",
        )

        assert dataset.metadata.provider == Provider.SPORTEC
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.metadata.periods) == 2
        assert len(dataset.records) == 6
        assert (
            dataset.metadata.orientation == Orientation.ACTION_EXECUTING_TEAM
        )
        assert dataset.metadata.periods[0] == Period(
            id=1,
            start_timestamp=0.04,
            end_timestamp=0.12,
            attacking_direction=AttackingDirection.HOME_AWAY,
        )
        assert dataset.metadata.periods[1] == Period(
            id=2,
            start_timestamp=5800.16,
            end_timestamp=5800.24,
            attacking_direction=AttackingDirection.AWAY_HOME,
        )

        # make sure data is loaded correctly (including flip y-axis)
        home_player = dataset.metadata.teams[0].players[0]
        assert dataset.records[0].players_coordinates[home_player] == Point(
            x=0.00082, y=1 - 0.48238
        )

        away_player = dataset.metadata.teams[1].players[0]
        assert dataset.records[0].players_coordinates[away_player] == Point(
            x=0.90509, y=1 - 0.47462
        )

        assert dataset.records[0].ball_coordinates == Point(
            x=0.45472, y=1 - 0.38709
        )

        # make sure player data is only in the frame when the player is at the pitch
        assert "home_14" not in [
            player.player_id
            for player in dataset.records[0].players_coordinates.keys()
        ]
        assert "home_14" in [
            player.player_id
            for player in dataset.records[3].players_coordinates.keys()
        ]
