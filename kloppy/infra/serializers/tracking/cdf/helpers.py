from kloppy.domain import PositionType, Ground

PERIODS_MAP = {
    1: "first_half",
    2: "second_half",
    3: "first_half_extratime",
    4: "second_half_extratime",
    5: "shootout",
}


def extract_team_players(team):
    """Extract player IDs from a team."""
    return [player.player_id for player in team.players]


def get_player_coordinates(frame, ground: Ground):
    """Create player data list for a team from frame coordinates."""
    players = []
    for player, coordinates in frame.players_coordinates.items():
        if player.team.ground == ground:
            players.append(
                {
                    "id": player.player_id,
                    "x": round(coordinates.x, 3),
                    "y": round(coordinates.y, 3),
                    "position": player.starting_position.code,
                }
            )
    return players


def get_ball_coordinates(frame):
    if frame.ball_coordinates is not None:
        return {
            "x": round(frame.ball_coordinates.x, 3),
            "y": round(frame.ball_coordinates.y, 3),
            "z": round(frame.ball_coordinates.z, 3),
        }

    # TODO: set to None after new CDF validator update
    return {"x": None, "y": None, "z": None}


def initialize_period_tracking(periods):
    """Initialize tracking dictionaries for all periods."""
    period_ids = [period.id for period in periods]
    return {
        "start_frame_id": {pid: None for pid in period_ids},
        "end_frame_id": {pid: None for pid in period_ids},
        "normalized_start_frame_id": {pid: None for pid in period_ids},
        "normalized_end_frame_id": {pid: None for pid in period_ids},
        "offset": {pid: 0 for pid in period_ids},
    }


def update_period_tracking(period_tracking, period_id, original_frame_id):
    """Update period tracking information for the current frame."""
    if period_tracking["start_frame_id"][period_id] is None:
        period_tracking["start_frame_id"][period_id] = original_frame_id

        if (
            period_id > 1
            and period_tracking["end_frame_id"][period_id - 1] is not None
        ):
            prev_period_length = (
                period_tracking["end_frame_id"][period_id - 1]
                - period_tracking["start_frame_id"][period_id - 1]
                + 1
            )
            period_tracking["offset"][period_id] = (
                period_tracking["offset"][period_id - 1] + prev_period_length
            )

        period_tracking["normalized_start_frame_id"][period_id] = (
            period_tracking["offset"][period_id]
        )

    period_tracking["end_frame_id"][period_id] = original_frame_id

    normalized_frame_id = (
        original_frame_id - period_tracking["start_frame_id"][period_id]
    ) + period_tracking["offset"][period_id]

    period_tracking["normalized_end_frame_id"][period_id] = normalized_frame_id

    return normalized_frame_id


def get_starting_formation(team_players) -> str:
    """
    determine the starting formation if not define.

    Args:
        team: The team on which we want to infer the formation.

    Returns:
        formation: the infered formation.
    """
    default_formation = "4-3-3"

    defender = midfielder = attacker = 0
    for player in team_players:
        if player.starting_position.position_group == None:
            continue
        elif player.starting_position.position_group == PositionType.Attacker:
            attacker += 1
        elif (
            player.starting_position.position_group == PositionType.Midfielder
        ):
            midfielder += 1
        elif player.starting_position.position_group == PositionType.Defender:
            defender += 1
    if defender + midfielder + attacker == 10:
        return f"{defender}-{midfielder}-{attacker}"
    elif defender + midfielder + attacker != 10:
        return default_formation
    return default_formation


def build_periods_info(dataset, period_tracking, home_team, away_team):
    """Build period information for metadata."""
    periods_info = []
    for period in dataset.metadata.periods:
        periods_info.append(
            {
                "period": PERIODS_MAP[period.id],
                "play_direction": "left_right",
                "start_time": str(
                    dataset.metadata.date + period.start_timestamp
                ),
                "end_time": str(dataset.metadata.date + period.end_timestamp),
                "start_frame_id": period_tracking["normalized_start_frame_id"][
                    period.id
                ],
                "end_frame_id": period_tracking["normalized_end_frame_id"][
                    period.id
                ],
                "left_team_id": home_team.team_id,
                "right_team_id": away_team.team_id,
            }
        )
    return periods_info


def build_whistles(periods_info):
    """Build whistle events from period information."""
    whistles = []
    for period in periods_info:
        whistles.append(
            {
                "type": period["period"],
                "sub_type": "start",
                "time": period["start_time"],
            }
        )
        whistles.append(
            {
                "type": period["period"],
                "sub_type": "end",
                "time": period["end_time"],
            }
        )
    return whistles


def get_starters_and_formation(team, first_frame):
    """
    Extract starter IDs and determine formation from first frame.

    Returns:
        tuple: (set of starter player IDs, formation string)
    """
    team_starters = {
        player.player_id
        for player, _ in first_frame.players_coordinates.items()
        if player.team == team
    }

    starters_list = [p for p in team.players if p.player_id in team_starters]

    formation = team.starting_formation or get_starting_formation(
        starters_list
    )

    return team_starters, formation


def build_team_players_metadata(team, starters):
    """Build player metadata for a team."""
    players = []
    for player in team.players:
        players.append(
            {
                "id": player.player_id,
                "team_id": team.team_id,
                "jersey_number": player.jersey_no,
                "is_starter": player.player_id in starters,
            }
        )
    return players
