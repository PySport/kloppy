"""XML parser for Stats Perform MA1 feeds."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from kloppy.domain import Ground, Period, Player, PositionType, Score, Team
from kloppy.exceptions import DeserializationError

from ..formation_mapping import (
    FormationType,
    formation_name_mapping,
    formation_position_mapping,
)
from .base import OptaXMLParser


class MA1XMLParser(OptaXMLParser):
    """Extract data from a Stats Perform MA1 data stream."""

    def extract_periods(self) -> List[Period]:
        parsed_periods = []
        live_data = self.root.liveData
        match_details = live_data.matchDetails
        periods = match_details.periods
        for period in periods.iterchildren(tag="period"):
            parsed_periods.append(
                Period(
                    id=int(period.get("id")),
                    start_timestamp=datetime.strptime(
                        period.get("start"), "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc),
                    end_timestamp=datetime.strptime(
                        period.get("end"), "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc),
                )
            )
        return parsed_periods

    def extract_score(self) -> Optional[Score]:
        return None

    def extract_lineups(self) -> Tuple[Team, Team]:
        teams = {}
        for parsed_team in self._parse_teams():
            team_id = parsed_team["team_id"]
            teams[team_id] = Team(
                team_id=team_id,
                name=parsed_team["name"],
                ground=(
                    Ground.HOME
                    if parsed_team["ground"] == "home"
                    else Ground.AWAY
                ),
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

    def _parse_teams(self) -> List[Dict[str, Any]]:
        parsed_teams = []
        match_info = self.root.matchInfo
        teams = match_info.contestants.iterchildren(tag="contestant")

        team_formations = {}
        live_data = self.root.liveData
        line_ups = live_data.iterchildren(tag="lineUp")
        for line_up in line_ups:
            team_id = line_up.get("contestantId")
            raw_formation = line_up.get("formationUsed")
            formation = formation_name_mapping.get(
                raw_formation, FormationType.UNKNOWN
            )
            team_formations[team_id] = formation

        for team in teams:
            team_attributes = team.attrib
            team_id = team_attributes["id"]
            parsed_teams.append(
                {
                    "team_id": team_id,
                    "name": team_attributes["name"],
                    "ground": team_attributes["position"],
                    "starting_formation": team_formations[team_id],
                }
            )
        return parsed_teams

    def _parse_players(self) -> List[Dict[str, Any]]:
        parsed_players = []
        live_data = self.root.liveData
        line_ups = live_data.iterchildren(tag="lineUp")
        for line_up in line_ups:
            team_id = line_up.get("contestantId")
            raw_formation = line_up.get("formationUsed")
            formation = formation_name_mapping.get(
                raw_formation, FormationType.UNKNOWN
            )

            players = line_up.iterchildren(tag="player")
            for player in players:
                player_attributes = player.attrib
                player_id = player_attributes["playerId"]

                if "formationPlace" in player_attributes:
                    player_position = (
                        formation_position_mapping[formation][
                            int(player_attributes["formationPlace"])
                        ]
                        if formation != FormationType.UNKNOWN
                        else PositionType.Unknown
                    )
                    starting = True
                else:
                    player_position = None
                    starting = False
                parsed_players.append(
                    {
                        "player_id": player_id,
                        "team_id": team_id,
                        "jersey_no": int(player_attributes["shirtNumber"]),
                        "name": player_attributes["matchName"],
                        "first_name": player_attributes["shortFirstName"]
                        if "shortFirstName" in player_attributes
                        else player_attributes["firstName"],
                        "last_name": player_attributes["shortLastName"]
                        if "shortLastName" in player_attributes
                        else player_attributes["lastName"],
                        "starting": starting,
                        "position": player_position,
                    }
                )
        return parsed_players
