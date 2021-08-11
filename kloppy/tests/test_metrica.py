import os

from kloppy import MetricaTrackingSerializer, MetricaEventsJsonSerializer
from kloppy.domain import (
    Period,
    Provider,
    AttackingDirection,
    Orientation,
    Point,
    EventType,
    SetPieceType,
    BodyPart,
)
from kloppy.domain.models.common import DatasetType


class TestMetricaTracking:
    def test_correct_deserialization(self):
        base_dir = os.path.dirname(__file__)

        serializer = MetricaTrackingSerializer()

        with open(
            f"{base_dir}/files/metrica_home.csv", "rb"
        ) as raw_data_home, open(
            f"{base_dir}/files/metrica_away.csv", "rb"
        ) as raw_data_away:
            dataset = serializer.deserialize(
                inputs={
                    "raw_data_home": raw_data_home,
                    "raw_data_away": raw_data_away,
                }
            )
        assert dataset.metadata.provider == Provider.METRICA
        assert dataset.dataset_type == DatasetType.TRACKING
        assert len(dataset.records) == 6
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation == Orientation.FIXED_HOME_AWAY
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


class TestMetricaEvent:
    def test_correct_deserialization(self):

        base_dir = os.path.dirname(__file__)

        serializer = MetricaEventsJsonSerializer()

        with open(
            f"{base_dir}/files/metrica_metadata.xml", "rb"
        ) as metadata, open(
            f"{base_dir}/files/metrica_events.json", "rb"
        ) as event_data:

            dataset = serializer.deserialize(
                inputs={"metadata": metadata, "event_data": event_data}
            )

        assert dataset.metadata.provider == Provider.METRICA
        assert dataset.dataset_type == DatasetType.EVENT
        assert len(dataset.events) == 3684
        assert len(dataset.metadata.periods) == 2
        assert dataset.metadata.orientation is None
        assert dataset.metadata.teams[0].name == "Team A"
        assert dataset.metadata.teams[1].name == "Team B"

        player = dataset.metadata.teams[0].players[0]
        assert player.player_id == "P3578"
        assert player.jersey_no == 11
        assert str(player) == "Player 11"
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

        assert dataset.events[1].coordinates.x == 0.50125

        # Check the qualifiers
        assert dataset.records[1].qualifiers[0].value == SetPieceType.KICK_OFF
        assert dataset.records[100].qualifiers[0].value == BodyPart.HEAD
