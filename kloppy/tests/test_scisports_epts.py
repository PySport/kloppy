from datetime import timedelta

from kloppy import scisports
from kloppy.domain import Provider, Point


class TestSciSportsEPTSTracking:
    def test_deserialize_basic(self, base_dir):
        meta = base_dir / "files/scisports_epts_metadata.xml"
        raw = base_dir / "files/scisports_epts_positions.txt"

        dataset = scisports.load_tracking(
            meta_data=meta, raw_data=raw, limit=100
        )

        assert dataset.metadata.provider == Provider.SCISPORTS
        assert len(dataset.records) == 100
        assert dataset.metadata.frame_rate == 25
        assert len(dataset.metadata.teams) == 2
        assert len(dataset.metadata.periods) >= 2

        first_frame = dataset.records[0]
        assert first_frame.frame_id == 44585
        # First frames are pre-period; timestamp should be absolute time (frame/frame_rate)
        assert first_frame.period is None
        assert first_frame.timestamp == timedelta(seconds=44585 / 25)

        # Find first in-period frame and verify timestamp reset to 0
        first_in_period = next(
            f for f in dataset.records if f.period is not None
        )
        assert first_in_period.timestamp == timedelta(seconds=0)

        assert first_frame.ball_coordinates.x is not None
        assert first_frame.ball_coordinates.y is not None

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
        assert first_p1.players_data[home_gk].coordinates == Point(
            x=34.17, y=8.36
        )
        assert first_p1.players_data[away_gk].coordinates == Point(
            x=35.33, y=85.39
        )

        assert first_p2.players_data[home_gk].coordinates == Point(
            x=32.25, y=89.15
        )
        assert first_p2.players_data[away_gk].coordinates == Point(
            x=34.23, y=3.88
        )
