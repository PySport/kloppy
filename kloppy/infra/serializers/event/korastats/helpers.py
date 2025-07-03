from typing import List, Dict

from kloppy.domain import (
    Team,
    Period,
    Point,
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


def check_pass_receiver(pass_event: Dict, teams: List[Team], next_event: Dict):
    passer_team = get_team_by_id(pass_event["team_id"], teams)
    receiver_team = get_team_by_id(next_event["team_id"], teams)
    if passer_team == receiver_team:
        receiver_coordinates = Point(next_event["x"], next_event["y"])
        receiver_player = receiver_team.get_player_by_id(
            next_event["player_id"]
        )
    else:
        receiver_coordinates = Point(
            100 - next_event["x"], 100 - next_event["y"]
        )
        receiver_player = None

    return receiver_player, receiver_coordinates
