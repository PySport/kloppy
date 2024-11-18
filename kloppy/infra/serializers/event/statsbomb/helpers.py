from datetime import timedelta
from typing import List, Dict, Optional

from kloppy.domain import (
    Point,
    Point3D,
    Team,
    Event,
    Frame,
    Period,
    Player,
    PlayerData,
    PositionType,
)
from kloppy.exceptions import DeserializationError

OPEN_COMPETITIONS_PATH = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json"
OPEN_MATCHES_PATH = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/{competition_id}/{season_id}.json"

import requests as re


def get_response(path):
    response = re.get(path)
    response.raise_for_status()
    data = response.json()
    return data


def parse_str_ts(timestamp: str) -> float:
    """Parse a HH:mm:ss string timestamp into number of seconds."""
    h, m, s = timestamp.split(":")
    return timedelta(seconds=int(h) * 3600 + int(m) * 60 + float(s))


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


def parse_coordinates(
    coordinates: List[float], fidelity_version: int
) -> Point:
    """Parse coordinates into a kloppy Point.

    Coordinates are cell-based, so 1,1 (low-granularity) or 0.1,0.1
    (high-granularity) is the top-left square 'yard' of the field (in
    landscape), even though 0,0 is the true coordinate of the corner flag.

    [1, 120] x [1, 80]
    +-----+-----+
    | 1,1 | 2,1 |
    +-----+-----+
    | 1,2 | 2,2 |
    +-----+-----+
    """
    cell_side = 0.1 if fidelity_version == 2 else 1.0
    cell_relative_center = cell_side / 2
    if len(coordinates) == 2:
        return Point(
            x=coordinates[0] - cell_relative_center,
            y=coordinates[1] - cell_relative_center,
        )
    elif len(coordinates) == 3:
        # A coordinate in the goal frame, only used for the end location of
        # Shot events. The y-coordinates and z-coordinates are always detailed
        # to a tenth of a yard.
        return Point3D(
            x=coordinates[0] - cell_relative_center,
            y=coordinates[1] - 0.05,
            z=coordinates[2] - 0.05,
        )
    else:
        raise DeserializationError(
            f"Unknown coordinates format: {coordinates}"
        )


def parse_freeze_frame(
    freeze_frame: List[Dict],
    fidelity_version: int,
    home_team: Team,
    away_team: Team,
    event: Event,
    visible_area: Optional[List] = None,
) -> Frame:
    """Parse a freeze frame into a kloppy Frame."""
    players_data = {}

    def get_player_from_freeze_frame(player_data, team, i):
        if "player" in player_data:
            return team.get_player_by_id(player_data["player"]["id"])
        elif player_data.get("actor"):
            return event.player
        elif player_data.get("keeper"):
            return team.get_player_by_position(
                position=PositionType.Goalkeeper, time=event.time
            )
        else:
            return Player(
                player_id=f"T{team.team_id}-E{event.event_id}-{i}",
                team=team,
                jersey_no=None,
            )

    for i, freeze_frame_player in enumerate(freeze_frame):
        is_teammate = (event.team == home_team) == freeze_frame_player[
            "teammate"
        ]
        freeze_frame_team = home_team if is_teammate else away_team

        player = get_player_from_freeze_frame(
            freeze_frame_player, freeze_frame_team, i
        )

        players_data[player] = PlayerData(
            coordinates=parse_coordinates(
                freeze_frame_player["location"], fidelity_version
            )
        )

    if event.player not in players_data:
        players_data[event.player] = PlayerData(coordinates=event.coordinates)

    FREEZE_FRAME_FPS = 25
    frame_id = int(
        event.period.start_timestamp.total_seconds()
        + event.timestamp.total_seconds() * FREEZE_FRAME_FPS
    )

    return Frame(
        frame_id=frame_id,
        ball_coordinates=Point3D(
            x=event.coordinates.x, y=event.coordinates.y, z=0
        ),
        players_data=players_data,
        period=event.period,
        timestamp=event.timestamp,
        ball_state=event.ball_state,
        ball_owning_team=event.ball_owning_team,
        other_data={"visible_area": visible_area},
    )


def parse_open_data(
    competition_id: int = None, season_id: int = None, fmt="dataframe"
):
    try:
        from statsbombpy import sb
        from statsbombpy.api_client import NoAuthWarning
    except ImportError:
        print("Please install the statsbombpy library to use this function.")
        return

    all_matches = []
    try:
        if competition_id is not None and season_id is not None:
            matches = sb.matches(
                competition_id=competition_id, season_id=season_id, fmt=fmt
            )
            all_matches.append(matches)
        elif competition_id is None and season_id is None:
            import warnings

            competitions = sb.competitions(fmt="dict")
            for competition in competitions.values():
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=NoAuthWarning)
                    competition_id = competition["competition_id"]
                    season_id = competition["season_id"]
                    matches = sb.matches(
                        competition_id=competition_id,
                        season_id=season_id,
                        fmt=fmt,
                    )
                    if fmt == "dataframe":
                        if not "competition_id" in matches.columns:
                            matches["competition_id"] = competition_id
                        if not "season_id" in matches.columns:
                            matches["season_id"] = season_id

                    elif fmt == "dict":
                        if not "competition_id" in matches:
                            matches["competition_id"] = competition_id
                        if not "season_id" in matches:
                            matches["season_id"] = season_id
                    else:
                        raise ValueError(
                            "Invalid format. Use 'dataframe' or 'dict'."
                        )
                    all_matches.append(matches)
        else:
            raise ValueError(
                "Invalid input: Both competition_id and season_id must either be provided together or omitted together."
            )

        if fmt == "dataframe":
            try:
                import pandas as pd
            except ImportError:
                print(
                    "Please install the pandas library to use this function."
                )
                return
            combined_matches = pd.concat(all_matches, ignore_index=True)
            return combined_matches
        elif fmt == "dict":
            return all_matches
        else:
            raise ValueError("Invalid format. Use 'dataframe' or 'dict'.")

    except Exception as e:
        raise RuntimeError(f"An error occurred while fetching data: {e}")
