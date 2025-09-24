"""Helper functions for SciSports event deserialization."""

from typing import Dict, List, Optional

from kloppy.domain import Team, Period


def get_team_by_id(team_id: int, teams: Dict[str, Team]) -> Optional[Team]:
    """Get team by ID from teams dictionary"""
    return teams.get(str(team_id))


def get_period_by_id(
    period_id: int, periods: List[Period]
) -> Optional[Period]:
    """Get period by ID from periods list"""
    for period in periods:
        if period.id == period_id:
            return period
    return None
