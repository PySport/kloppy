"""Base class for all parsers that can handle Tracab metadata files.

A parser reads a single metadata file and should extend the 'TracabMetadataParser'
class to extract the data about periods, lineups, pitch dimensions, etc.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import IO, List, Optional, Tuple

from kloppy.domain import Orientation, Period, Score, Team


class TracabMetadataParser(ABC):
    """Extract data from a tracab metadata file."""

    def __init__(self, feed: IO[bytes]) -> None:
        """Initialize the parser with the data stream.

        Args:
            feed : The metadata of a game to parse.
        """

    @abstractmethod
    def extract_periods(self) -> List[Period]:
        """Extract the periods of the game."""

    def extract_score(self) -> Optional[Score]:
        """Extract the game's score."""
        return None

    def extract_date(self) -> Optional[datetime]:
        """Extract the game's date."""
        return None

    def extract_game_week(self) -> Optional[str]:
        """Extract the game week."""
        return None

    def extract_game_id(self) -> Optional[str]:
        """Extract the game's id."""
        return None

    @abstractmethod
    def extract_lineups(self) -> Tuple[Team, Team]:
        """Extract the home and away team."""

    @abstractmethod
    def extract_pitch_dimensions(self) -> Tuple[float, float]:
        """Extract the pitch size as (length, width)."""

    @abstractmethod
    def extract_frame_rate(self) -> int:
        """Extract the tracking data's frame rate."""

    def extract_orientation(self) -> Optional[Orientation]:
        """Extract the orientation of the data."""
        return None
