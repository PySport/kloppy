import re
from typing import Dict

from kloppy.domain import (
    DatasetTransformer,
    Frame,
    PlayerData,
    Point,
    Point3D,
)
from kloppy.domain.services.frame_factory import create_frame


def _sanitize(identifier: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]", "_", identifier)


def build_players_data(
    row: Dict, metadata, swap_coordinates: bool = False
) -> Dict:
    other_sensors = [
        sensor
        for sensor in metadata.sensors
        if sensor.sensor_id not in ["position", "distance", "speed"]
    ]

    players_data: Dict = {}
    for team in metadata.teams:
        for player in team.players:
            safe_player_id = _sanitize(player.player_id)
            other_data = {}
            for sensor in other_sensors:
                safe_channel = _sanitize(sensor.channels[0].channel_id)
                player_sensor_field_str = (
                    f"player_{safe_player_id}_{safe_channel}"
                )
                player_sensor_val = row.get(player_sensor_field_str)
                other_data.update({sensor.sensor_id: player_sensor_val})

            # Get raw coordinates
            raw_x = row.get(f"player_{safe_player_id}_x")
            raw_y = row.get(f"player_{safe_player_id}_y")

            # Swap coordinates if needed (for SciSports)
            if swap_coordinates:
                x, y = raw_y, raw_x
            else:
                x, y = raw_x, raw_y

            players_data[player] = PlayerData(
                coordinates=(
                    Point(x=x, y=y)
                    if f"player_{safe_player_id}_x" in row
                    else None
                ),
                speed=(
                    row.get(f"player_{safe_player_id}_s")
                    if f"player_{safe_player_id}_s" in row
                    else None
                ),
                distance=(
                    row.get(f"player_{safe_player_id}_d")
                    if f"player_{safe_player_id}_d" in row
                    else None
                ),
                other_data=other_data,
            )

    return players_data


def create_frame_from_row(
    row: Dict,
    metadata,
    transformer: DatasetTransformer,
    swap_coordinates: bool = False,
) -> Frame:
    timestamp = row["timestamp"]

    period = None
    if metadata.periods and row.get("period_id"):
        for p in metadata.periods:
            if p.id == row["period_id"]:
                period = p
                break

    players_data = build_players_data(row, metadata, swap_coordinates)

    # Get raw ball coordinates
    raw_ball_x = row.get("ball_x")
    raw_ball_y = row.get("ball_y")

    # Swap ball coordinates if needed (for SciSports)
    if swap_coordinates:
        ball_x, ball_y = raw_ball_y, raw_ball_x
    else:
        ball_x, ball_y = raw_ball_x, raw_ball_y

    frame = create_frame(
        frame_id=row["frame_id"],
        timestamp=timestamp,
        ball_owning_team=None,
        ball_state=None,
        period=period,
        players_data=players_data,
        other_data={},
        ball_coordinates=Point3D(
            x=ball_x, y=ball_y, z=row.get("ball_z_estimate")
        ),
    )

    if transformer:
        frame = transformer.transform_frame(frame)

    return frame
