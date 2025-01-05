from typing import List, Dict, Union

from kloppy.domain import Team, Period, Point, FormationType, PositionType
from kloppy.exceptions import DeserializationError

formation_mapping: Dict[str, FormationType] = {}

position_types_mapping: Dict[str, PositionType] = {
    "TW": PositionType.Goalkeeper,
    "IVR": PositionType.RightCenterBack,
    "IVL": PositionType.LeftCenterBack,
    "STR": PositionType.Striker,
    "STL": PositionType.LeftForward,
    "STZ": PositionType.Striker,
    "ZO": PositionType.CenterAttackingMidfield,
    "LV": PositionType.LeftBack,
    "RV": PositionType.RightBack,
    "DMR": PositionType.RightDefensiveMidfield,
    "DRM": PositionType.RightDefensiveMidfield,
    "DML": PositionType.LeftDefensiveMidfield,
    "DLM": PositionType.LeftDefensiveMidfield,
    "ORM": PositionType.RightMidfield,
    "OLM": PositionType.LeftMidfield,
    "RA": PositionType.RightWing,
    "LA": PositionType.LeftWing,
}


def get_team_by_id(team_id: int, teams: List[Team]) -> Team:
    """Get a team by its id."""
    if str(team_id) == teams[0].team_id:
        return teams[0]
    elif str(team_id) == teams[1].team_id:
        return teams[1]
    else:
        raise DeserializationError(f"Unknown team_id {team_id}")


def get_period_by_id(period_id: int, periods: List[Period]) -> Period:
    """Get a period by its id."""
    for period in periods:
        if period.id == period_id:
            return period
    raise DeserializationError(f"Unknown period_id {period_id}")


def parse_coordinates(raw_coordinates: Dict[str, float]) -> Point:
    return Point(
        x=float(raw_coordinates["x"]),
        y=float(raw_coordinates["y"]),
    )
