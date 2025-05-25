"""Base class for all parsers that can handle Tracab raw data files.

A parser reads a single data file and should extend the 'TracabDataParser'
class to extract the tracking data frames.
"""

from abc import ABC, abstractmethod
from typing import IO, Iterator, List, Tuple

from kloppy.domain import Frame, Period, Team


class TracabDataParser(ABC):
    """Extract data from a Tracab tracking data stream."""

    def __init__(
        self,
        feed: IO[bytes],
        periods: List[Period],
        teams: Tuple[Team, Team],
        frame_rate: int,
    ) -> None:
        """Initialize the parser with the data stream and metadata.

        Args:
            feed : The data stream of a game to parse.
            periods : The periods of the game.
            teams : The home and away teams.
            frame_rate : The frame rate of the tracking data.
        """
        self.periods = periods
        self.teams = teams
        self.frame_rate = frame_rate

    @abstractmethod
    def extract_frames(
        self, sample_rate: float, only_alive: bool
    ) -> Iterator[Frame]:
        """Extract all frames."""
