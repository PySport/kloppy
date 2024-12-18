"""JSON parser for Stats Perform MA1 feeds."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from kloppy.domain import Ground, Period, Player, Score, Team
from kloppy.exceptions import DeserializationError

from .base import OptaJSONParser


class MA1JSONParser(OptaJSONParser):
    """Extract data from a Stats Perform MA1 data stream."""

    def extract_periods(self) -> List[Period]:
        live_data = self.root["liveData"]
        match_details = live_data["matchDetails"]
        parsed_periods = []
        for period in match_details["period"]:
            period_start_raw = period.get("start")
            period_end_raw = period.get("end")
            if not period_end_raw:
                game_end_suspension_stop = next(
                    suspension_stop
                    for suspension_stop in period["suspension"]
                    if suspension_stop["reason"] == "early end"
                )
                period_end_raw = game_end_suspension_stop["start"]
            parsed_periods.append(
                Period(
                    id=period["id"],
                    start_timestamp=datetime.strptime(
                        period_start_raw, "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                    if period_start_raw
                    else None,
                    end_timestamp=datetime.strptime(
                        period_end_raw, "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                    if period_end_raw
                    else None,
                )
            )
        return parsed_periods

    def extract_score(self) -> Optional[Score]:
        live_data = self.root["liveData"]
        match_details = live_data["matchDetails"]
        home_score = match_details["scores"]["total"]["home"]
        away_score = match_details["scores"]["total"]["away"]
        if home_score is None or away_score is None:
            return None
        return Score(home=home_score, away=away_score)

    def extract_lineups(self) -> Tuple[Team, Team]:
        teams = {}
        for parsed_team in self._parse_teams():
            team_id = parsed_team["team_id"]
            teams[team_id] = Team(
                team_id=team_id,
                name=parsed_team["name"],
                ground=Ground.HOME
                if parsed_team["ground"] == "home"
                else Ground.AWAY,
            )

        for parsed_player in self._parse_players():
            player_id = parsed_player["player_id"]
            team_id = parsed_player["team_id"]
            team = teams[team_id]
            player = Player(
                player_id=player_id,
                team=team,
                jersey_no=parsed_player["jersey_no"],
                name=parsed_player["name"],
                first_name=parsed_player["first_name"],
                last_name=parsed_player["last_name"],
                starting=parsed_player["starting"],
                starting_position=parsed_player["position"],
            )
            team.players.append(player)

        home_team = next(
            (team for team in teams.values() if team.ground == Ground.HOME),
            None,
        )
        away_team = next(
            (team for team in teams.values() if team.ground == Ground.AWAY),
            None,
        )
        if home_team is None:
            raise DeserializationError("Could not find home team")
        if away_team is None:
            raise DeserializationError("Could not find away team")
        if len(home_team.players) == 0 or len(away_team.players) == 0:
            raise DeserializationError("Lineup incomplete")
        return home_team, away_team

    def extract_date(self) -> Optional[datetime]:
        """Return the date of the game."""
        if "matchInfo" in self.root and "date" in self.root["matchInfo"]:
            return datetime.strptime(
                self.root["matchInfo"]["date"], "%Y-%m-%dZ"
            ).replace(tzinfo=timezone.utc)
        else:
            return None

    def extract_game_week(self) -> Optional[str]:
        """Return the game_week of the game."""
        if "matchInfo" in self.root and "week" in self.root["matchInfo"]:
            return self.root["matchInfo"]["week"]
        else:
            return None

    def extract_game_id(self) -> Optional[str]:
        """Return the game_id of the game."""
        if "matchInfo" in self.root and "id" in self.root["matchInfo"]:
            return self.root["matchInfo"]["id"]
        else:
            return None

    def _parse_teams(self) -> List[Dict[str, Any]]:
        parsed_teams = []
        match_info = self.root["matchInfo"]
        teams = match_info["contestant"]
        for team in teams:
            team_id = team["id"]
            parsed_teams.append(
                {
                    "team_id": team_id,
                    "name": team["name"],
                    "ground": team["position"],
                }
            )
        return parsed_teams

    def _parse_players(self) -> List[Dict[str, Any]]:
        parsed_players = []
        live_data = self.root["liveData"]
        line_ups = live_data["lineUp"]
        for line_up in line_ups:
            team_id = line_up["contestantId"]
            players = line_up["player"]
            for player in players:
                player_id = player["playerId"]
                parsed_players.append(
                    {
                        "player_id": player_id,
                        "team_id": team_id,
                        "jersey_no": player["shirtNumber"],
                        "name": player["matchName"],
                        "first_name": player["shortFirstName"],
                        "last_name": player["shortLastName"],
                        "starting": player["position"] != "Substitute",
                        "position": player["position"],
                    }
                )
        return parsed_players
