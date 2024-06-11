"""Base class for all Opta(-derived) event stream parsers.

A parser reads a single data file and should extend the 'OptaParser' class to
extract data about players, teams and events that is encoded in the file.
"""
import json
from typing import Tuple, List, Optional, IO, Dict

from lxml import objectify

from kloppy.domain import Team, Score, Period

from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OptaEvent:
    """A raw Opta event."""

    id: str
    event_id: int
    type_id: int
    period_id: int
    time_min: int
    time_sec: int
    x: float
    y: float
    timestamp: datetime
    last_modified: datetime
    contestant_id: Optional[str] = None
    player_id: Optional[str] = None
    outcome: Optional[int] = None
    qualifiers: Dict[int, str] = field(default_factory=dict)


class OptaParser:
    """Extract data from an Opta data stream.

    Args:
        feed : The data stream of a game to parse.
    """

    def __init__(self, feed: IO[bytes]) -> None:
        raise NotImplementedError

    def extract_periods(self) -> List[Period]:
        """Return the periods of the game."""
        raise NotImplementedError

    def extract_score(self) -> Optional[Score]:
        """Return the score of the game."""
        return None

    def extract_lineups(self) -> Tuple[Team, Team]:
        """Return the home and away team."""
        raise NotImplementedError

    def extract_events(self) -> List[OptaEvent]:
        """Return all events."""
        raise NotImplementedError


class OptaJSONParser(OptaParser):
    """Extract data from an Opta JSON data stream.

    Args:
        feed : The data stream of a game to parse.

    Attributes:
        root : The root of the JSON data.
    """

    def __init__(self, feed: IO[bytes]) -> None:
        self.root = json.load(feed)


class OptaXMLParser(OptaParser):
    """Extract data from an Opta XML data stream.

    Args:
        feed : The data stream of a game to parse.

    Attributes:
        root : The root of the XML tree.
    """

    def __init__(self, feed: IO[bytes]) -> None:
        self.root = objectify.fromstring(feed.read())
