import bisect
from datetime import timedelta
from typing import List, Dict, Tuple
import re

from kloppy.domain import (
    Team,
    Period,
    Point,
    Point3D,
    ShotResult,
)
from kloppy.exceptions import DeserializationError


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


def parse_timestamp(ts_str: str) -> Tuple[timedelta, int]:
    """
    Parse a football clock timestamp into:
      - elapsed time (timedelta)
      - period_id (1..4)

    Supported forms:
      • "MM:SS.sss"
      • "MM:SS.sss (+MM:SS.sss)"
    """
    half_len = 45  # minutes per half
    et_len = 15  # minutes per extra-time period

    # 1) stoppage-time form?
    m = re.match(
        r"^\s*(\d+):(\d+(?:\.\d+))\s*\(\+(\d+):(\d+(?:\.\d+))\)\s*$", ts_str
    )
    if m:
        main_min, main_sec = int(m.group(1)), float(m.group(2))
        add_min, add_sec = int(m.group(3)), float(m.group(4))

        main_secs = main_min * 60 + main_sec
        add_secs = add_min * 60 + add_sec

        # determine period_id from the main minute
        if main_min <= half_len:
            period_id = 1
        elif main_min <= 2 * half_len:
            period_id = 2
        elif main_min <= 2 * half_len + et_len:
            period_id = 3
        else:
            period_id = 4

        # compute elapsed:
        #  - in regulation: cumulative
        #  - in ET: subtract the pre-ET 90 min so it's time into that ET-half
        if main_min <= 2 * half_len:
            total_secs = main_secs + add_secs
        else:
            total_secs = main_secs + add_secs - (2 * half_len) * 60

        whole = int(total_secs)
        micros = int((total_secs - whole) * 1e6)
        return timedelta(seconds=whole, microseconds=micros), period_id

    # 2) plain form: "MM:SS.sss"
    m = re.match(r"^\s*(\d+):(\d+(?:\.\d+))\s*$", ts_str)
    if not m:
        raise ValueError(f"Unrecognized timestamp: {ts_str!r}")

    total_min = int(m.group(1))
    secs = float(m.group(2))

    # figure out which period we're in
    if total_min < half_len:
        period_id = 1
        start_min = 0
    elif total_min < 2 * half_len:
        period_id = 2
        start_min = half_len
    elif total_min < 2 * half_len + et_len:
        period_id = 3
        start_min = 2 * half_len
    else:
        period_id = 4
        start_min = 2 * half_len + et_len

    # elapsed _within_ that period
    in_period_min = total_min - start_min
    period_secs = in_period_min * 60 + secs

    whole = int(period_secs)
    micros = int((period_secs - whole) * 1e6)
    return timedelta(seconds=whole, microseconds=micros), period_id


def parse_coordinates(raw_coordinates: Dict[str, float]) -> Point:
    return Point(
        x=float(raw_coordinates["x"]),
        y=float(raw_coordinates["y"]),
    )


def parse_shot_end_coordinates(
    shot_info: Dict,
    shot_result,
) -> (Point, ShotResult):
    """Parse coordinates into a kloppy Point."""
    from kloppy.infra.serializers.event.impect.specification import SHOT

    shot_target_point = shot_info["targetPoint"]
    if shot_target_point:
        y_coordinate = shot_target_point["y"]
        z_coordinate = shot_target_point["z"]
        shot_end_coordinates = Point3D(100, y_coordinate, z_coordinate)
        if shot_result == SHOT.RESULT.SUCCESS:
            result = ShotResult.GOAL
        # elif is_own_goal:
        #     result = ShotResult.OWN_GOAL
        elif shot_info["woodwork"]:
            result = ShotResult.POST
        elif abs(y_coordinate) < 3.66 and z_coordinate < 2.44:
            result = ShotResult.SAVED
        else:
            result = ShotResult.OFF_TARGET
    else:
        shot_end_coordinates = None
        result = ShotResult.OFF_TARGET

    return shot_end_coordinates, result


def insert(event, sorted_events):
    pos = bisect.bisect_left([e.time for e in sorted_events], event.time)
    sorted_events.insert(pos, event)
