"""XML parser for Opta F7 feeds."""
from datetime import datetime
from typing import Any, Dict, Tuple, List, Optional

from lxml import objectify

from .base import OptaXMLParser
from kloppy.domain import (
    Team,
    Ground,
    FormationType,
    Player,
    Position,
    Score,
    Period,
)
from kloppy.exceptions import DeserializationError

document_path = objectify.ObjectPath("SoccerFeed.SoccerDocument")
matchdata_path = objectify.ObjectPath("SoccerFeed.SoccerDocument.MatchData")
match_result_path = objectify.ObjectPath(
    "SoccerFeed.SoccerDocument.MatchData.MatchInfo.Result"
)


def _parse_f7_datetime(dt_str: str) -> datetime:
    return datetime.strptime(dt_str, "%Y%m%dT%H%M%S%z")


class F7XMLParser(OptaXMLParser):
    """Extract data from a Opta F7 data stream.

    Parameters
    ----------
    path : str
        Path of the data file.
    """

    def extract_periods(self) -> List[Period]:
        periods = {
            i: Period(id=i, start_timestamp=None, end_timestamp=None)
            for i in range(1, 5)
        }
        match_stats = matchdata_path.find(self.root).iterchildren("Stat")
        for stat in match_stats:
            if stat.attrib["Type"] == "first_half_start":
                periods[1].start_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "first_half_end":
                periods[1].end_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "second_half_start":
                periods[2].start_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "second_half_end":
                periods[2].end_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "first_half_extra_start":
                periods[3].start_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "first_half_extra_end":
                periods[3].end_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "second_half_extra_start":
                periods[4].start_timestamp = _parse_f7_datetime(stat.text)
            elif stat.attrib["Type"] == "second_half_extra_end":
                periods[4].end_timestamp = _parse_f7_datetime(stat.text)
        periods = [
            period
            for period in periods.values()
            if period.start_timestamp is not None
        ]

        match_result_type = list(match_result_path.find(self.root))[0].attrib[
            "Type"
        ]
        if match_result_type == "PenaltyShootout":
            periods.append(
                Period(id=5, start_timestamp=None, end_timestamp=None)
            )

        return periods

    def extract_score(self) -> Optional[Score]:
        team_elms = matchdata_path.find(self.root).iterchildren("TeamData")
        home_score = None
        away_score = None
        for team_elm in team_elms:
            if team_elm.attrib["Side"] == "Home":
                home_score = int(team_elm.attrib["Score"])
            elif team_elm.attrib["Side"] == "Away":
                away_score = int(team_elm.attrib["Score"])
            else:
                raise DeserializationError(
                    f"Unknown side: {team_elm.attrib['Side']}"
                )
        if home_score is None or away_score is None:
            return None
        return Score(home=home_score, away=away_score)

    def extract_lineups(self) -> Tuple[Team, Team]:
        """Return a dictionary with all available teams.

        Returns
        -------
        dict
            A mapping between team IDs and the information available about
            each team in the data stream.
        """
        team_elms = matchdata_path.find(self.root).iterchildren("TeamData")
        home_team = None
        away_team = None
        for team_elm in team_elms:
            if team_elm.attrib["Side"] == "Home":
                home_team = self._team_from_xml_elm(team_elm)
            elif team_elm.attrib["Side"] == "Away":
                away_team = self._team_from_xml_elm(team_elm)
            else:
                raise DeserializationError(
                    f"Unknown side: {team_elm.attrib['Side']}"
                )
        if home_team is None:
            raise DeserializationError("Could not find home team")
        if away_team is None:
            raise DeserializationError("Could not find away team")
        if len(home_team.players) == 0 or len(away_team.players) == 0:
            raise DeserializationError("Lineup incomplete")
        return home_team, away_team

    def _team_from_xml_elm(self, team_elm: Any) -> Team:
        # This should not happen here
        team_name, team_players = self._parse_team_players(
            team_elm.attrib["TeamRef"]
        )
        team = Team(
            team_id=str(team_elm.attrib["TeamRef"].lstrip("t")),
            name=team_name,
            ground=Ground.HOME
            if team_elm.attrib["Side"] == "Home"
            else Ground.AWAY,
            starting_formation=FormationType(
                "-".join(list(team_elm.attrib["Formation"]))
            ),
        )
        team.players = [
            Player(
                player_id=player_elm.attrib["PlayerRef"].lstrip("p"),
                team=team,
                jersey_no=int(player_elm.attrib["ShirtNumber"]),
                first_name=team_players[player_elm.attrib["PlayerRef"]][
                    "first_name"
                ],
                last_name=team_players[player_elm.attrib["PlayerRef"]][
                    "last_name"
                ],
                starting=True
                if player_elm.attrib["Status"] == "Start"
                else False,
                position=Position(
                    position_id=player_elm.attrib["Formation_Place"],
                    name=player_elm.attrib["Position"],
                    coordinates=None,
                ),
            )
            for player_elm in team_elm.find("PlayerLineUp").iterchildren(
                "MatchPlayer"
            )
        ]
        return team

    def _parse_team_players(
        self, team_ref: str
    ) -> Tuple[str, Dict[str, Dict[str, str]]]:
        team_elms = list(document_path.find(self.root).iterchildren("Team"))
        for team_elm in team_elms:
            if team_elm.attrib["uID"] == team_ref:
                team_name = str(team_elm.find("Name"))
                players = {
                    player_elm.attrib["uID"]: dict(
                        first_name=str(
                            player_elm.find("PersonName").find("First")
                        ),
                        last_name=str(
                            player_elm.find("PersonName").find("Last")
                        ),
                    )
                    for player_elm in team_elm.iterchildren("Player")
                }
                break
        else:
            raise DeserializationError(
                f"Could not parse players for {team_ref}"
            )

        return team_name, players
