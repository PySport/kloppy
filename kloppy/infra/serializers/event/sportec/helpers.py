from datetime import datetime

from kloppy.domain import (
    Period,
    Team,
)
from kloppy.exceptions import DeserializationError


def get_team_by_id(team_id: int, teams: list[Team]) -> Team:
    """Get a team by its id."""
    if str(team_id) == teams[0].team_id:
        return teams[0]
    elif str(team_id) == teams[1].team_id:
        return teams[1]
    else:
        raise DeserializationError(f"Unknown team_id {team_id}")


def get_period_by_timestamp(
    timestamp: datetime, periods: list[Period]
) -> Period:
    """Get a period by its id."""
    for period in periods:
        if period.start_timestamp <= timestamp <= period.end_timestamp:
            return period
    raise DeserializationError(
        f"Could not find period for timestamp {timestamp}"
    )


def parse_datetime(timestamp: str) -> datetime:
    """Parse a ISO format datetime string into a datetime object."""
    return datetime.fromisoformat(timestamp)
