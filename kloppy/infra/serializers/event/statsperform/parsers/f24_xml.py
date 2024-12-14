"""XML parser for Opta F24 feeds."""

from datetime import datetime
from typing import List, Optional

import pytz

from .base import OptaEvent, OptaXMLParser


def _parse_f24_datetime(dt_str: str) -> datetime:
    def zero_pad_milliseconds(timestamp):
        parts = timestamp.split(".")
        if len(parts) == 1:
            return timestamp + ".000"
        return ".".join(parts[:-1] + ["{:03d}".format(int(parts[-1]))])

    dt_str = zero_pad_milliseconds(dt_str)
    naive_datetime = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
    timezone = pytz.timezone("Europe/London")
    aware_datetime = timezone.localize(naive_datetime)
    return aware_datetime.astimezone(pytz.utc)


class F24XMLParser(OptaXMLParser):
    """Extract data from a Opta F24 data stream."""

    def extract_events(self) -> List[OptaEvent]:
        game_elm = self.root.find("Game")
        return [
            OptaEvent(
                id=event.attrib["id"],
                event_id=int(event.attrib["event_id"]),
                type_id=int(event.attrib["type_id"]),
                period_id=int(event.attrib["period_id"]),
                time_min=int(event.attrib["min"]),
                time_sec=int(event.attrib["sec"]),
                x=float(event.attrib["x"]),
                y=float(event.attrib["y"]),
                timestamp=_parse_f24_datetime(event.attrib["timestamp"]),
                last_modified=_parse_f24_datetime(
                    event.attrib["last_modified"]
                ),
                contestant_id=event.attrib.get("team_id"),
                player_id=event.attrib.get("player_id"),
                outcome=int(event.attrib["outcome"])
                if "outcome" in event.attrib
                else None,
                qualifiers={
                    int(
                        qualifier.attrib["qualifier_id"]
                    ): qualifier.attrib.get("value")
                    for qualifier in event.iterchildren("Q")
                },
            )
            for event in game_elm.iterchildren("Event")
        ]

    def extract_date(self) -> Optional[datetime]:
        """Return the date of the game."""
        game_elm = self.root.find("Game")
        if game_elm and "game_date" in game_elm.attrib:
            naive_datetime = datetime.strptime(
                game_elm.attrib["game_date"], "%Y-%m-%dT%H:%M:%S"
            )
            timezone = pytz.timezone("Europe/London")
            aware_datetime = timezone.localize(naive_datetime)
            return aware_datetime.astimezone(pytz.utc)
        else:
            return None

    def extract_game_week(self) -> Optional[str]:
        """Return the game_week of the game."""
        game_elm = self.root.find("Game")
        if game_elm and "matchday" in game_elm.attrib:
            return game_elm.attrib["matchday"]
        else:
            return None

    def extract_game_id(self) -> Optional[str]:
        """Return the game_id of the game."""
        game_elm = self.root.find("Game")
        if game_elm and "id" in game_elm.attrib:
            return game_elm.attrib["id"]
        else:
            return None
