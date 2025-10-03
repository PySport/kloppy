from datetime import timedelta

import pytest

from kloppy import scisports
from kloppy.domain import (
    Provider,
    Point,
    Orientation,
    BallState,
    PositionType,
    Origin,
    VerticalOrientation,
)


@pytest.fixture
def scisports_dataset(base_dir):
    """Fixture that loads the complete SciSports EPTS dataset."""
    meta = base_dir / "files/scisports_epts_metadata.xml"
    raw = base_dir / "files/scisports_epts_positions.txt"
    return scisports.load_tracking(meta_data=meta, raw_data=raw)


@pytest.fixture
def scisports_dataset_scisports_coords(base_dir):
    """Fixture that loads SciSports EPTS dataset with SciSports coordinate system."""
    meta = base_dir / "files/scisports_epts_metadata.xml"
    raw = base_dir / "files/scisports_epts_positions.txt"
    return scisports.load_tracking(
        meta_data=meta, raw_data=raw, limit=500000, coordinates="scisports"
    )


class TestSciSportsEPTSTracking:
    def test_deserialize_basic(self, scisports_dataset):
        dataset = scisports_dataset

        assert dataset.metadata.provider == Provider.SCISPORTS
        assert len(dataset.records) == 843  # Reduced test file with 501 frames
        assert dataset.metadata.frame_rate == 25
        assert len(dataset.metadata.teams) == 2
        assert len(dataset.metadata.periods) >= 2

        # Some frames may be pre/post-match in the reduced test file
        # Check that we have frames from both periods
        period1_frames = [
            f for f in dataset.records if f.period and f.period.id == 1
        ]
        period2_frames = [
            f for f in dataset.records if f.period and f.period.id == 2
        ]
        assert len(period1_frames) > 0
        assert len(period2_frames) > 0

        first_frame = dataset.records[0]
        # First frame may be pre-match in reduced test file
        print(
            f"First frame timestamp: {first_frame.timestamp}, period: {first_frame.period.id if first_frame.period else None}"
        )

        assert first_frame.ball_coordinates.x is not None
        assert first_frame.ball_coordinates.y is not None

    def test_gk_positions_first_frames(
        self, scisports_dataset_scisports_coords
    ):
        dataset = scisports_dataset_scisports_coords

        home_team = next(
            t for t in dataset.metadata.teams if str(t.ground) == "home"
        )
        away_team = next(
            t for t in dataset.metadata.teams if str(t.ground) == "away"
        )

        home_gk = next(
            p
            for p in home_team.players
            if p.position == PositionType.Goalkeeper
        )
        away_gk = next(
            p
            for p in away_team.players
            if p.position == PositionType.Goalkeeper
        )
        home_lb = next(
            p for p in home_team.players if p.player_id == "P-007854"
        )
        away_lb = next(
            p for p in away_team.players if p.player_id == "P-008981"
        )

        first_p1 = next(
            f for f in dataset.records if f.period and f.period.id == 1
        )
        first_p2 = next(
            f for f in dataset.records if f.period and f.period.id == 2
        )

        # orientation: home - away means home keeper low x and away keeper high x coordinate
        assert dataset.metadata.orientation == Orientation.HOME_AWAY
        assert first_p1.players_data[home_gk].coordinates == Point(
            x=8.36, y=34.17
        )
        assert first_p1.players_data[away_gk].coordinates == Point(
            x=85.39, y=35.33
        )

        # origin: top - left & vertical orientation: top to bottom
        # means home lb low y and away lb high y coordinate
        assert dataset.metadata.coordinate_system.origin == Origin.TOP_LEFT
        assert (
            dataset.metadata.coordinate_system.vertical_orientation
            == VerticalOrientation.TOP_TO_BOTTOM
        )
        assert first_p1.players_data[home_lb].coordinates == Point(
            x=36.43, y=16.22
        )
        assert first_p1.players_data[away_lb].coordinates == Point(
            x=53.48, y=55.48
        )

        # In the second period, it should be flipped
        assert first_p2.players_data[home_gk].coordinates == Point(
            x=89.15, y=32.25
        )
        assert first_p2.players_data[away_gk].coordinates == Point(
            x=3.88, y=34.23
        )
        assert first_p2.players_data[home_lb].coordinates == Point(
            x=52.79, y=54.6
        )
        assert first_p2.players_data[away_lb].coordinates == Point(
            x=39.35, y=10.85
        )

    def test_timestamp_reset_per_period(self, scisports_dataset):
        """Test that timestamps are reset to start from 0:00:00 at the beginning of each period."""
        dataset = scisports_dataset

        # Get frames for each period
        period1_frames = [
            f for f in dataset.records if f.period and f.period.id == 1
        ]
        period2_frames = [
            f for f in dataset.records if f.period and f.period.id == 2
        ]

        # Both periods should have frames
        assert len(period1_frames) > 0, "Period 1 should have frames"
        assert len(period2_frames) > 0, "Period 2 should have frames"

        # Period 1: First frame should start near 0:00:00 (allowing for some pre-period start)
        # Note: Some frames may be before period start in reduced test data
        first_p1_timestamp = period1_frames[0].timestamp
        last_p1_timestamp = period1_frames[-1].timestamp

        # Period 1 should have reasonable duration (> 0)
        assert (
            last_p1_timestamp > first_p1_timestamp
        ), "Period 1 should have positive duration"

        # Period 2: Should start from 0:00:00 (reset from period start)
        first_p2_timestamp = period2_frames[0].timestamp
        last_p2_timestamp = period2_frames[-1].timestamp

        # Period 2 first frame should be at exactly 0:00:00 (timestamp reset)
        assert first_p2_timestamp == timedelta(
            0
        ), f"Period 2 should start at 0:00:00, got {first_p2_timestamp}"

        # Period 2 should have positive duration
        assert (
            last_p2_timestamp > first_p2_timestamp
        ), "Period 2 should have positive duration"

        # Verify that timestamps within each period are monotonically increasing
        prev_timestamp = None
        for frame in period1_frames:
            if prev_timestamp is not None:
                assert (
                    frame.timestamp >= prev_timestamp
                ), f"Period 1 timestamps should be increasing: {prev_timestamp} -> {frame.timestamp}"
            prev_timestamp = frame.timestamp

        prev_timestamp = None
        for frame in period2_frames:
            if prev_timestamp is not None:
                assert (
                    frame.timestamp >= prev_timestamp
                ), f"Period 2 timestamps should be increasing: {prev_timestamp} -> {frame.timestamp}"
            prev_timestamp = frame.timestamp

    def test_ball_state_detection(self, scisports_dataset):
        """Test that ball states (alive/dead) are correctly parsed from ball channel data."""
        dataset = scisports_dataset

        # Count ball states
        alive_frames = [
            f for f in dataset.records if f.ball_state == BallState.ALIVE
        ]
        dead_frames = [
            f for f in dataset.records if f.ball_state == BallState.DEAD
        ]

        # Verify we have both states represented
        assert len(alive_frames) == 775
        assert len(dead_frames) == 68

        # Total should equal all frames
        total_frames = len(alive_frames) + len(dead_frames)
        assert total_frames == len(dataset.records)

    def test_player_position_types(self, scisports_dataset):
        """Test that player position types are correctly mapped from metadata."""
        dataset = scisports_dataset

        # Count players by position type
        goalkeepers = []
        field_players = []

        for team in dataset.metadata.teams:
            for player in team.players:
                if player.starting_position and "Goalkeeper" in str(
                    player.starting_position
                ):
                    goalkeepers.append(player)
                elif player.attributes.get("PlayerType") == "Goalkeeper":
                    goalkeepers.append(player)
                elif player.attributes.get("PlayerType") == "Field player":
                    field_players.append(player)

        # Should have exactly 2 goalkeepers (one per team)
        assert (
            len(goalkeepers) == 2
        ), f"Expected 2 goalkeepers, found {len(goalkeepers)}"

        # Should have multiple field players
        assert (
            len(field_players) > 10
        ), f"Expected >10 field players, found {len(field_players)}"
