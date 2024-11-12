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


def parse_open_matches(competition_id: int, season_id: int, detailed: bool):
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "Seems like you don't have pandas installed. Please"
            " install it using: pip install pandas"
        )
    except AttributeError:
        raise AttributeError(
            "Seems like you have an older version of pandas installed. Please"
            " upgrade to at least 1.5 using: pip install pandas>=1.5"
        )

    path = OPEN_MATCHES_PATH.format(
        competition_id=competition_id, season_id=season_id
    )
    matches = get_response(path)
    df = pd.json_normalize(matches, sep="_")

    # clean up column names
    for v in ["competition", "season", "home_team", "away_team"]:
        df.columns = [x.replace(f"{v}_{v}", v) for x in df.columns]

    if detailed:

        def __flatten_team_managers(df, team_type):
            # Normalize the team managers, explode to handle list entries within the column, and add prefix for clarity
            managers_expanded = pd.json_normalize(
                df[f"{team_type}_managers"].explode(), sep="_"
            ).add_prefix(f"{team_type}_manager_")
            return managers_expanded.reset_index(drop=True)

        # Normalize both home and away managers
        home_managers_expanded = __flatten_team_managers(df, "home_team")
        away_managers_expanded = __flatten_team_managers(df, "away_team")

        # Concatenate both expanded managers back to the original DataFrame, and drop the original manager columns
        df = pd.concat(
            [
                df.reset_index(drop=True),
                home_managers_expanded,
                away_managers_expanded,
            ],
            axis=1,
        )
        df.drop(
            columns=["home_team_managers", "away_team_managers"],
            inplace=True,
            errors="ignore",
        )
        return df
    else:
        return df[
            [
                "match_id",
                "match_date",
                "home_score",
                "away_score",
                "home_team_name",
                "home_team_id",
                "away_team_name",
                "away_team_id",
            ]
        ]


def parse_open_competitions(detailed: bool):
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "Seems like you don't have pandas installed. Please"
            " install it using: pip install pandas"
        )
    except AttributeError:
        raise AttributeError(
            "Seems like you have an older version of pandas installed. Please"
            " upgrade to at least 1.5 using: pip install pandas>=1.5"
        )

    competitions = get_response(OPEN_COMPETITIONS_PATH)
    df = pd.DataFrame(competitions).sort_values(
        by="match_available", ascending=False
    )
    if detailed:
        return df
    else:
        return df[
            [
                "competition_id",
                "season_id",
                "country_name",
                "competition_name",
                "season_name",
            ]
        ]
