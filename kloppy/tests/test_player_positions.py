from datetime import timedelta
from typing import Optional

import pytest

from kloppy.domain import (
    BallState,
    DatasetFlag,
    EventDataset,
    EventFactory,
    FormationType,
    Ground,
    KloppyCoordinateSystem,
    Metadata,
    Orientation,
    Period,
    Player,
    PositionType,
    Provider,
    Team,
    Time,
)
from kloppy.exceptions import DeserializationWarning

# (period id, minute, player id, replacement id, explicit position)
Substitution = tuple[int, int, Optional[str], str, Optional[PositionType]]


def build_dataset(
    substitutions: list[Substitution],
    formation_change: Optional[
        tuple[int, int, dict[Optional[str], PositionType]]
    ] = None,
) -> EventDataset:
    """Build a dataset where home players h1-h11 start as center backs and
    h12-h14 are substitutes, then apply the given events in order."""
    period1 = Period(
        id=1,
        start_timestamp=timedelta(0),
        end_timestamp=timedelta(minutes=45),
    )
    period2 = Period(
        id=2,
        start_timestamp=timedelta(0),
        end_timestamp=timedelta(minutes=45),
    )
    period1.set_refs(None, period2)
    period2.set_refs(period1, None)
    periods = {1: period1, 2: period2}

    home = Team(team_id="home", name="Home", ground=Ground.HOME)
    home.players = [
        Player(
            player_id=f"h{i}",
            team=home,
            jersey_no=i,
            starting=i <= 11,
            starting_position=PositionType.CenterBack if i <= 11 else None,
        )
        for i in range(1, 15)
    ]
    away = Team(team_id="away", name="Away", ground=Ground.AWAY)

    factory = EventFactory()
    generic_kwargs = dict(
        team=home,
        ball_owning_team=None,
        ball_state=BallState.DEAD,
        coordinates=None,
        raw_event=None,
        result=None,
        qualifiers=None,
    )
    events = []
    for index, (
        period_id,
        minute,
        player_id,
        replacement_id,
        position,
    ) in enumerate(substitutions):
        events.append(
            factory.build_substitution(
                event_id=f"substitution-{index}",
                period=periods[period_id],
                timestamp=timedelta(minutes=minute),
                player=home.get_player_by_id(player_id),
                replacement_player=home.get_player_by_id(replacement_id),
                position=position,
                **generic_kwargs,
            )
        )
    if formation_change:
        period_id, minute, player_positions = formation_change
        events.append(
            factory.build_formation_change(
                event_id="formation-change",
                period=periods[period_id],
                timestamp=timedelta(minutes=minute),
                player=None,
                formation_type=FormationType.FOUR_FOUR_TWO,
                player_positions={
                    home.get_player_by_id(player_id): position
                    for player_id, position in player_positions.items()
                },
                **generic_kwargs,
            )
        )

    coordinate_system = KloppyCoordinateSystem()
    metadata = Metadata(
        teams=[home, away],
        periods=[period1, period2],
        pitch_dimensions=coordinate_system.pitch_dimensions,
        orientation=Orientation.HOME_AWAY,
        flags=DatasetFlag(0),
        provider=Provider.OTHER,
        coordinate_system=coordinate_system,
        score=None,
        frame_rate=None,
    )
    return EventDataset(metadata=metadata, records=events)


def positions(dataset: EventDataset, player_id: str) -> list:
    """Return (start, end, position) per range of a home player, as strings."""
    player = dataset.metadata.teams[0].get_player_by_id(player_id)
    return [
        (str(start), str(end), position)
        for start, end, position in player.positions.ranges()
    ]


def players_on_pitch_at_end(dataset: EventDataset) -> int:
    period2 = dataset.metadata.periods[1]
    end = Time(period=period2, timestamp=timedelta(minutes=45))
    return sum(
        1
        for player in dataset.metadata.teams[0].players
        if player.positions.items and player.positions.value_at(end)
    )


class TestSubstitutionPositions:
    """Tests that inconsistent substitutions give a usable position timeline"""

    def test_consistent_substitution(self):
        """It should hand the player's position to the replacement"""
        dataset = build_dataset([(2, 10, "h1", "h12", None)])

        assert positions(dataset, "h1") == [
            ("P1T00:00", "P2T10:00", PositionType.CenterBack)
        ]
        assert positions(dataset, "h12") == [
            ("P2T10:00", "P2T45:00", PositionType.CenterBack)
        ]

    def test_substitution_recorded_twice(self):
        """It should keep the first recording when a substitution is repeated with swapped players"""
        with pytest.warns(DeserializationWarning, match="already on the pitch"):
            dataset = build_dataset(
                [
                    (1, 45, "h1", "h12", PositionType.LeftWing),
                    (1, 45, "h2", "h13", PositionType.RightWing),
                    (2, 0, "h2", "h12", None),
                    (2, 0, "h1", "h13", None),
                    (2, 20, "h12", "h14", None),
                ]
            )

        assert positions(dataset, "h12") == [
            ("P1T45:00", "P2T20:00", PositionType.LeftWing)
        ]
        assert positions(dataset, "h13") == [
            ("P1T45:00", "P2T45:00", PositionType.RightWing)
        ]
        assert positions(dataset, "h14") == [
            ("P2T20:00", "P2T45:00", PositionType.LeftWing)
        ]
        assert positions(dataset, "h1") == [
            ("P1T00:00", "P1T45:00", PositionType.CenterBack)
        ]
        dataset.aggregate("minutes_played", include_position=True)

    def test_explicit_position_for_replacement_on_pitch(self):
        """It should apply an explicit position as a position change when the replacement is already on the pitch"""
        with pytest.warns(DeserializationWarning, match="position change"):
            dataset = build_dataset(
                [(2, 10, "h12", "h2", PositionType.Striker)]
            )

        assert positions(dataset, "h2") == [
            ("P1T00:00", "P2T10:00", PositionType.CenterBack),
            ("P2T10:00", "P2T45:00", PositionType.Striker),
        ]
        assert positions(dataset, "h12") == []

    def test_player_not_on_pitch_substituted_off(self):
        """It should bring the replacement on as Unknown and leave an extra player on the pitch"""
        with pytest.warns(DeserializationWarning, match="is not on the pitch"):
            dataset = build_dataset([(2, 10, "h12", "h13", None)])

        assert positions(dataset, "h12") == []
        assert positions(dataset, "h13") == [
            ("P2T10:00", "P2T45:00", PositionType.Unknown)
        ]
        # The feed does not say who actually left the pitch.
        assert players_on_pitch_at_end(dataset) == 12
        dataset.aggregate("minutes_played", include_position=True)

    def test_player_not_in_lineup_substituted_off(self):
        """It should bring the replacement on when the player is missing from the lineup"""
        with pytest.warns(
            DeserializationWarning, match="Unknown player substituted off"
        ):
            dataset = build_dataset([(2, 10, None, "h13", None)])

        assert positions(dataset, "h13") == [
            ("P2T10:00", "P2T45:00", PositionType.Unknown)
        ]
        dataset.aggregate("minutes_played", include_position=True)

    def test_player_replaces_themselves(self):
        """It should ignore a substitution of a player by themselves"""
        with pytest.warns(DeserializationWarning, match="replaces themselves"):
            dataset = build_dataset([(2, 10, "h1", "h1", None)])

        assert positions(dataset, "h1") == [
            ("P1T00:00", "P2T45:00", PositionType.CenterBack)
        ]

    def test_substitutions_at_same_instant(self):
        """It should handle a replacement who is substituted again at the same instant"""
        dataset = build_dataset(
            [(2, 10, "h1", "h12", None), (2, 10, "h12", "h13", None)]
        )

        assert positions(dataset, "h12") == []
        assert positions(dataset, "h13") == [
            ("P2T10:00", "P2T45:00", PositionType.CenterBack)
        ]
        dataset.aggregate("minutes_played", include_position=True)


class TestFormationChangePositions:
    def test_player_not_in_lineup(self):
        """It should skip a formation change entry for a player missing from the lineup"""
        with pytest.warns(
            DeserializationWarning, match="Unknown player in formation change"
        ):
            dataset = build_dataset(
                [],
                formation_change=(
                    2,
                    10,
                    {None: PositionType.Striker, "h2": PositionType.LeftBack},
                ),
            )

        assert positions(dataset, "h2") == [
            ("P1T00:00", "P2T10:00", PositionType.CenterBack),
            ("P2T10:00", "P2T45:00", PositionType.LeftBack),
        ]
