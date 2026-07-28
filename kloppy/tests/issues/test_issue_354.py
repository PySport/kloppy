from datetime import timedelta

from kloppy.domain import (
    Ground,
    Period,
    Player,
    Point,
    PositionType,
    Team,
)
from kloppy.infra.serializers.tracking.skillcorner import (
    SkillCornerDeserializer,
)


class TestIssue354:
    def test_v2_player_resolution_with_existing_group_name(self):
        """
        Verify V2 frame deserialization resolves known players by trackable_object even
        when the frame record already includes a group_name ("home team" / "away team").

        Previously, frame records with a non-empty group_name skipped metadata-based player lookup,
        which could leave 'player' unassigned (causing UnboundLocalError) or reuse a player
        from a previous record.
        """
        home_team = Team(team_id=1, name="Home", ground=Ground.HOME)
        away_team = Team(team_id=2, name="Away", ground=Ground.AWAY)
        home_player = Player(
            player_id="home-1",
            team=home_team,
            jersey_no=1,
            starting_position=PositionType.Unknown,
        )
        away_player = Player(
            player_id="away-1",
            team=away_team,
            jersey_no=1,
            starting_position=PositionType.Unknown,
        )
        teams = [home_team, away_team]
        players = {"HOME": {10: home_player}, "AWAY": {20: away_player}}

        frame = SkillCornerDeserializer._get_frame_data_v2(
            teams=teams,
            teamdict={1: "home_team", 2: "away_team"},
            players=players,
            player_id_to_team_dict={10: 1, 20: 2},
            periods={
                1: Period(
                    id=1,
                    start_timestamp=timedelta(seconds=0),
                    end_timestamp=timedelta(seconds=1),
                )
            },
            player_dict={},
            anon_players={"HOME": {}, "AWAY": {}},
            ball_id=99,
            referee_dict={},
            frame={
                "possession": {"trackable_object": 10, "group": "home team"},
                "frame": 1,
                "period": 1,
                "time": "00:00.1",
                # Frame records include existing 'group_name' strings
                "data": [
                    {
                        "x": 1,
                        "y": 2,
                        "trackable_object": 10,
                        "track_id": 10,
                        "group_name": "home team",
                    },
                    {
                        "x": 3,
                        "y": 4,
                        "trackable_object": 20,
                        "track_id": 20,
                        "group_name": "away team",
                    },
                ],
            },
            only_alive=False,
        )

        assert frame.players_data[home_player].coordinates == Point(x=1, y=2)
        assert frame.players_data[away_player].coordinates == Point(x=3, y=4)
