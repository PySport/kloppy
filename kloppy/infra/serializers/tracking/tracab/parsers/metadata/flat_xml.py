from datetime import datetime, timezone
from typing import IO, List, Optional, Tuple

from lxml import objectify

from kloppy.domain import Ground, Orientation, Period, Team

from .base import TracabMetadataParser
from .common import create_period, create_team


class TracabFlatXMLMetadataParser(TracabMetadataParser):
    """Extract metadata from an XML file with a flat metadata object.

    Expected XML structure:

        <root>
            <GameID>13331</GameID>
            <CompetitionID>55</CompetitionID>
            ...
        </root>

    Args:
        feed : The data stream of a game to parse.

    Attributes:
        root : The root of the XML tree.
    """

    def __init__(self, feed: IO[bytes]) -> None:
        self.root = objectify.fromstring(feed.read())

    def extract_periods(self) -> List[Period]:
        frame_rate = self.extract_frame_rate()
        periods = []
        for i in [1, 2, 3, 4, 5]:
            start_frame_id = int(self.root[f"Phase{i}StartFrame"])
            end_frame_id = int(self.root[f"Phase{i}EndFrame"])
            period = create_period(i, start_frame_id, end_frame_id, frame_rate)
            if period:
                periods.append(period)
        return periods

    def extract_date(self) -> Optional[datetime]:
        date = datetime.strptime(
            str(self.root["Kickoff"]), "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        return date

    def extract_game_id(self) -> Optional[str]:
        game_id = str(self.root["GameID"])
        return game_id

    def extract_lineups(self) -> Tuple[Team, Team]:
        start_frame_id = int(self.root["Phase1StartFrame"])
        if hasattr(self.root, "HomeTeam") and hasattr(self.root, "AwayTeam"):
            home_team = create_team(
                self.root["HomeTeam"],
                Ground.HOME,
                start_frame_id,
                id_suffix="ID",
                player_item="item",
            )
            away_team = create_team(
                self.root["AwayTeam"],
                Ground.AWAY,
                start_frame_id,
                id_suffix="ID",
                player_item="item",
            )
        else:
            home_team = Team(team_id="home", name="home", ground=Ground.HOME)
            away_team = Team(team_id="away", name="away", ground=Ground.AWAY)
        return (home_team, away_team)

    def extract_pitch_dimensions(self) -> Tuple[float, float]:
        pitch_size_width = float(self.root["PitchShortSide"]) / 100
        pitch_size_length = float(self.root["PitchLongSide"]) / 100
        return pitch_size_length, pitch_size_width

    def extract_frame_rate(self) -> int:
        frame_rate = int(self.root["FrameRate"])
        return frame_rate

    def extract_orientation(self) -> Orientation:
        if self.root.get("Phase1HomeGKLeft", None) is not None:
            orientation = (
                Orientation.HOME_AWAY
                if bool(self.root["Phase1HomeGKLeft"])
                else Orientation.AWAY_HOME
            )
            return orientation
        else:
            return None
