from datetime import timedelta
import math

from kloppy import scisports
from kloppy.domain import Provider, Point, Orientation, AttackingDirection


class TestSciSportsEPTSTracking:
    def test_deserialize_basic(self, base_dir):
        meta = base_dir / "files/scisports_epts_metadata.xml"
        raw = base_dir / "files/scisports_epts_positions.txt"

        dataset = scisports.load_tracking(
            meta_data=meta, raw_data=raw, limit=100
        )

        assert dataset.metadata.provider == Provider.SCISPORTS
        assert len(dataset.records) == 26  # Only frames that belong to periods
        assert dataset.metadata.frame_rate == 25
        assert len(dataset.metadata.teams) == 2
        assert len(dataset.metadata.periods) >= 2

        # All frames should now have periods (no pre/post-match frames)
        assert all(frame.period is not None for frame in dataset.records)

        first_frame = dataset.records[0]
        # First frame should now be the first frame of period 1
        assert first_frame.period is not None
        assert first_frame.period.id == 1
        # Timestamp should be relative to period start (0 for first frame)
        assert first_frame.timestamp == timedelta(seconds=0)

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
        assert first_p1.players_data[home_gk].coordinates == Point(
            x=8.36, y=34.17
        )
        assert first_p1.players_data[away_gk].coordinates == Point(
            x=85.39, y=35.33
        )

        assert first_p2.players_data[home_gk].coordinates == Point(
            x=89.15, y=32.25
        )
        assert first_p2.players_data[away_gk].coordinates == Point(
            x=3.88, y=34.23
        )
