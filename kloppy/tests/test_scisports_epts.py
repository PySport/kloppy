from datetime import timedelta
import math

from kloppy import scisports
from kloppy.domain import Provider, Point, Orientation, AttackingDirection


class TestSciSportsEPTSTracking:
    def test_deserialize_basic(self, base_dir):
        meta = base_dir / "files/scisports_epts_metadata.xml"
        raw = base_dir / "files/scisports_epts_positions.txt"

        dataset = scisports.load_tracking(meta_data=meta, raw_data=raw)

        assert dataset.metadata.provider == Provider.SCISPORTS
        assert len(dataset.records) == 501  # Reduced test file with 501 frames
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

        # Verify orientation is correctly determined from first frame analysis
        assert dataset.metadata.orientation == Orientation.AWAY_HOME

    def test_gk_positions_first_frames(self, base_dir):
        meta = base_dir / "files/scisports_epts_metadata.xml"
        raw = base_dir / "files/scisports_epts_positions.txt"

        dataset = scisports.load_tracking(
            meta_data=meta, raw_data=raw, limit=500000, coordinates="scisports"
        )

        home_team = next(
            t for t in dataset.metadata.teams if str(t.ground) == "home"
        )
        away_team = next(
            t for t in dataset.metadata.teams if str(t.ground) == "away"
        )

        home_gk = next(
            p
            for p in home_team.players
            if p.attributes.get("PlayerType") == "Goalkeeper"
        )
        away_gk = next(
            p
            for p in away_team.players
            if p.attributes.get("PlayerType") == "Goalkeeper"
        )

        first_p1 = next(
            f for f in dataset.records if f.period and f.period.id == 1
        )
        first_p2 = next(
            f for f in dataset.records if f.period and f.period.id == 2
        )

        # Expected coordinates when using scisports coordinate system (meters, origin bottom-left)
        # Coordinates are now correctly swapped: X spans field length, Y spans field width
        # Updated for reduced test file with different frame selection
        assert first_p1.players_data[home_gk].coordinates == Point(
            x=2.84, y=34.51
        )
        assert first_p1.players_data[away_gk].coordinates == Point(
            x=79.58, y=35.03
        )

        assert first_p2.players_data[home_gk].coordinates == Point(
            x=89.15, y=32.25
        )
        assert first_p2.players_data[away_gk].coordinates == Point(
            x=3.88, y=34.23
        )
