import json
from datetime import datetime, timezone
from typing import IO, List, Optional, Tuple

from kloppy.domain import Ground, Orientation, Period, Team

from .base import TracabMetadataParser
from .common import create_period, create_team


class TracabJSONMetadataParser(TracabMetadataParser):
    """Extract metadata from a JSON file.

    Args:
        feed : The data stream of a game to parse.

    Attributes:
        root : The root of the JSON data.
    """

    def __init__(self, feed: IO[bytes]) -> None:
        self.root = json.load(feed)

    def extract_periods(self) -> List[Period]:
        frame_rate = self.extract_frame_rate()
        periods: List[Period] = []
        for period_id in (1, 2, 3, 4):
            period_start_frame = self.root[f"Phase{period_id}StartFrame"]
            period_end_frame = self.root[f"Phase{period_id}EndFrame"]
            period = create_period(
                period_id, period_start_frame, period_end_frame, frame_rate
            )
            if period is not None:
                periods.append(period)
        return periods

    def extract_date(self) -> Optional[datetime]:
        date = self.root.get("Kickoff", None)
        if date is not None:
            return datetime.strptime(date, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )

        return None

    def extract_game_id(self) -> Optional[str]:
        game_id = self.root.get("GameID", None)
        if game_id is not None:
            return str(game_id)
        return None

    def extract_lineups(self) -> Tuple[Team, Team]:
        start_frame_id = self.root["Phase1StartFrame"]
        home_team = create_team(
            self.root["HomeTeam"],
            Ground.HOME,
            start_frame_id,
            id_suffix="ID",
            player_item=None,
        )
        away_team = create_team(
            self.root["AwayTeam"],
            Ground.AWAY,
            start_frame_id,
            id_suffix="ID",
            player_item=None,
        )
        return (home_team, away_team)

    def extract_pitch_dimensions(self) -> Tuple[float, float]:
        pitch_size_length = float(self.root["PitchLongSide"]) / 100
        pitch_size_width = float(self.root["PitchShortSide"]) / 100
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
