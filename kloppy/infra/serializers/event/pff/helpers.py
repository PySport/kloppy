from datetime import timedelta
from typing import Dict, List, Optional

from kloppy.domain import (
    ActionValue,
    Event,
    Frame,
    Period,
    Player,
    PlayerData,
    Point,
    Point3D,
    PositionType,
    Team,
)
from kloppy.domain.services.frame_factory import create_frame
from kloppy.exceptions import DeserializationError


def get_team_by_id(team_id: int | None, teams: list[Team]) -> Team | None:
    """Get a team by its id."""
    if team_id is None:
        return None
    if str(team_id) == teams[0].team_id:
        return teams[0]
    elif str(team_id) == teams[1].team_id:
        return teams[1]
    else:
        raise DeserializationError(f"Unknown team_id {team_id}")


def get_period_by_id(period_id: int, periods: list[Period]) -> Period:
    """Get a period by its id."""
    for period in periods:
        if period.id == period_id:
            return period
    raise DeserializationError(f"Unknown period_id {period_id}")


def parse_coordinates(
    player: Player | None, raw_event: dict[str, object]
) -> Point | None:
    """Parse PFF coordinates into a kloppy Point."""
    if player is None:
        return None

    players = raw_event["homePlayers"] + raw_event["awayPlayers"]

    try:
        player_dict = next(
            player_dict
            for player_dict in players
            if str(player_dict["playerId"]) == player.player_id
        )

        return Point(
            x=player_dict["x"],
            y=player_dict["y"],
        )
    except StopIteration:
        print(player)
        raise DeserializationError(f"Unknown player {player}")


def parse_freeze_frame(
    freeze_frame: List[Dict],
    home_team: Team,
    away_team: Team,
    event: Event,
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

    FREEZE_FRAME_FPS = 29.97

    frame_id = int(
        event.period.start_timestamp.total_seconds()
        + event.timestamp.total_seconds() * FREEZE_FRAME_FPS
    )

    frame = create_frame(
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

    return frame
