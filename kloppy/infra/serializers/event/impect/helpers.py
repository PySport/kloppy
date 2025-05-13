from typing import List, Dict

from kloppy.domain import (
    Team,
    Period,
    Point,
    FormationType,
    PositionType,
    Point3D,
    ShotResult,
)
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


def parse_shot_end_coordinates(
    shot_info: Dict, is_goal: bool = False, is_own_goal: bool = False
) -> (Point, ShotResult):
    """Parse coordinates into a kloppy Point."""

    y_coordinate = shot_info["targetPoint"]["y"]
    z_coordinate = shot_info["targetPoint"]["z"]
    shot_end_coordinates = Point3D(100, y_coordinate, z_coordinate)

    if is_goal:
        result = ShotResult.GOAL
    elif is_own_goal:
        result = ShotResult.OWN_GOAL
    elif shot_info["woodwork"]:
        result = ShotResult.POST
    elif abs(y_coordinate) < 3.66 and z_coordinate < 2.44:
        result = ShotResult.SAVED
    else:
        result = ShotResult.OFF_TARGET

    return shot_end_coordinates, result
