from datetime import datetime, timezone
from typing import IO, List, Optional, Tuple

from lxml import objectify

from kloppy.domain import Ground, Period, Team

from .base import TracabMetadataParser
from .common import create_period, create_team


class TracabHierarchicalXMLMetadataParser(TracabMetadataParser):
    """Extract metadata from an XML file with a hierarchical metadata object.

    Expected XML structure:

        <match iId="1" ...>
            <period iId="1" iStartFrame="1848508" iEndFrame="1916408"/>
            ...
        </match>

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
        for period in self.root.match.iterchildren(tag="period"):
            start_frame_id = int(period.attrib["iStartFrame"])
            end_frame_id = int(period.attrib["iEndFrame"])
            period_obj = create_period(
                int(period.attrib["iId"]),
                start_frame_id,
                end_frame_id,
                frame_rate,
            )
            if period_obj:
                periods.append(period_obj)
        return periods

    def extract_date(self) -> Optional[datetime]:
        date = datetime.strptime(
            self.root.match.attrib["dtDate"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        return date

    def extract_game_id(self) -> Optional[str]:
        game_id = self.root.match.attrib["iId"]
        return game_id

    def extract_lineups(self) -> Tuple[Team, Team]:
        start_frame_id = 0
        for period in self.root.match.iterchildren(tag="period"):
            start_frame_id = int(period.attrib["iStartFrame"])
            break
        if hasattr(self.root, "HomeTeam") and hasattr(self.root, "AwayTeam"):
            home_team = create_team(
                self.root["HomeTeam"],
                Ground.HOME,
                start_frame_id,
                id_suffix="Id",
                player_item="Player",
            )
            away_team = create_team(
                self.root["AwayTeam"],
                Ground.AWAY,
                start_frame_id,
                id_suffix="Id",
                player_item="Player",
            )
        else:
            home_team = Team(team_id="home", name="home", ground=Ground.HOME)
            away_team = Team(team_id="away", name="away", ground=Ground.AWAY)

        return (home_team, away_team)

    def extract_pitch_dimensions(self) -> Tuple[float, float]:
        pitch_size_width = float(
            self.root.match.attrib["fPitchXSizeMeters"].replace(",", ".")
        )
        pitch_size_height = float(
            self.root.match.attrib["fPitchYSizeMeters"].replace(",", ".")
        )
        return pitch_size_width, pitch_size_height

    def extract_frame_rate(self) -> int:
        frame_rate = int(self.root.match.attrib["iFrameRateFps"])
        return frame_rate
