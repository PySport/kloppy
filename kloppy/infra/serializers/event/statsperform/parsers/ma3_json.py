"""JSON parser for Stats Perform MA3 feeds."""
import pytz
from datetime import datetime
from typing import List

from .base import OptaJSONParser, OptaEvent


def _parse_ma3_datetime(dt_str: str) -> datetime:
    try:
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=pytz.utc
        )

    except ValueError:
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=pytz.utc
        )


class MA3JSONParser(OptaJSONParser):
    """Extract data from a Stats Perform MA3 data stream."""

    def extract_events(self) -> List[OptaEvent]:
        live_data = self.root["liveData"]
        return [
            OptaEvent(
                id=event["id"],
                event_id=event["eventId"],
                type_id=event["typeId"],
                period_id=event["periodId"],
                time_min=event["timeMin"],
                time_sec=event["timeSec"],
                x=event["x"],
                y=event["y"],
                timestamp=_parse_ma3_datetime(event["timeStamp"]),
                last_modified=_parse_ma3_datetime(event["lastModified"]),
                contestant_id=event.get("contestantId"),
                player_id=event.get("playerId"),
                outcome=event.get("outcome"),
                qualifiers={
                    qualifier["qualifierId"]: qualifier.get("value")
                    for qualifier in event["qualifier"]
                },
            )
            for event in live_data["event"]
        ]
