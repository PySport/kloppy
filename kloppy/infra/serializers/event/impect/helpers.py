import bisect
import re
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

from kloppy.domain import (
    Period,
    Point,
    Point3D,
    ShotResult,
    Team,
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
      - elapsed time within the period (timedelta) - period-relative for events
      - period_id (1..4)

    Supported forms:
      - "MM:SS.sss"
      - "MM:SS.sss (+MM:SS.sss)"
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

        # compute time within the period
        if main_min <= half_len:
            # Period 1: time from start of match
            period_secs = main_secs + add_secs
        elif main_min <= 2 * half_len:
            # Period 2: time from start of period 2 (subtract 45 minutes)
            period_secs = main_secs + add_secs - (half_len * 60)
        elif main_min <= 2 * half_len + et_len:
            # Period 3: time from start of period 3 (subtract 90 minutes)
            period_secs = main_secs + add_secs - (2 * half_len * 60)
        else:
            # Period 4: time from start of period 4 (subtract 105 minutes)
            period_secs = main_secs + add_secs - ((2 * half_len + et_len) * 60)

        whole = int(period_secs)
        micros = int((period_secs - whole) * 1e6)
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


def parse_cumulative_timestamp(ts_str: str) -> Tuple[timedelta, int]:
    """
    Parse a football clock timestamp into:
      - cumulative elapsed time (timedelta) - for period creation
      - period_id (1..4)

    Supported forms:
      - "MM:SS.sss"
      - "MM:SS.sss (+MM:SS.sss)"
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

        # compute cumulative elapsed time
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
    elif total_min < 2 * half_len:
        period_id = 2
    elif total_min < 2 * half_len + et_len:
        period_id = 3
    else:
        period_id = 4

    # cumulative time from match start
    cumulative_secs = total_min * 60 + secs

    whole = int(cumulative_secs)
    micros = int((cumulative_secs - whole) * 1e6)
    return timedelta(seconds=whole, microseconds=micros), period_id


def parse_coordinates(raw_coordinates: Dict[str, float]) -> Point:
    return Point(
        x=float(raw_coordinates["x"]),
        y=float(raw_coordinates["y"]),
    )


def parse_shot_end_coordinates(
    shot_info: Dict,
    shot_result,
) -> Tuple[Optional[Point], ShotResult]:
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
        elif shot_info.get("woodwork"):
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
