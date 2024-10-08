"""XML parser for Opta F24 feeds."""
import pytz
from datetime import datetime
from typing import List

from kloppy.domain import Period
from .base import OptaXMLParser, OptaEvent


def _parse_f24_datetime(dt_str: str) -> datetime:
    def zero_pad_milliseconds(timestamp):
        parts = timestamp.split(".")
        if len(parts) == 1:
            return timestamp + ".000"
        return ".".join(parts[:-1] + ["{:03d}".format(int(parts[-1]))])

    dt_str = zero_pad_milliseconds(dt_str)
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=pytz.utc
    )


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
