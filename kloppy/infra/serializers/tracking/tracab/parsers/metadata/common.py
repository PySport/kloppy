import html
from datetime import timedelta
from typing import Dict, Optional

from kloppy.domain import (
    Period,
    Player,
    PositionType,
    Team,
)

position_types_mapping: Dict[str, PositionType] = {
    "G": PositionType.Goalkeeper,
    "D": PositionType.Defender,
    "M": PositionType.Midfielder,
    "A": PositionType.Attacker,
}


def create_team(
    team_data, ground, start_frame_id, id_suffix="Id", player_item="Player"
):
    """
    Create a team object from team data
    """
    team = Team(
        team_id=str(team_data[f"Team{id_suffix}"]),
        name=html.unescape(team_data["ShortName"]),
        ground=ground,
    )

    players = (
        team_data["Players"][player_item]
        if player_item
        else team_data["Players"]
    )
    team.players = [
        Player(
            player_id=str(player[f"Player{id_suffix}"]),
            team=team,
            first_name=html.unescape(player["FirstName"]),
            last_name=html.unescape(player["LastName"]),
            name=html.unescape(player["FirstName"] + " " + player["LastName"]),
            jersey_no=int(player["JerseyNo"]),
            starting=player["StartFrameCount"] == start_frame_id,
            starting_position=position_types_mapping.get(
                player.get("StartingPosition"), PositionType.Unknown
            ),
        )
        for player in players
    ]

    return team


def create_period(
    period_id: int, start_frame: int, end_frame: int, frame_rate: int
) -> Optional[Period]:
    """
    Create a period object if frames are valid.
    """
    if start_frame != 0 or end_frame != 0:
        return Period(
            id=period_id,
            start_timestamp=timedelta(seconds=start_frame / frame_rate),
            end_timestamp=timedelta(seconds=end_frame / frame_rate),
        )
    return None
