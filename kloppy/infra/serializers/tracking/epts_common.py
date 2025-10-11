import re
from datetime import timedelta
from typing import Dict, IO, Iterator, List

from kloppy.domain import (
    BallState,
    DatasetTransformer,
    Frame,
    PlayerData,
    Point,
    Point3D,
)
from kloppy.domain.services.frame_factory import create_frame


def _sanitize(identifier: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]", "_", identifier)


def _determine_ball_state(row: Dict) -> BallState:
    """Determine ball state from ball channel data."""
    # Check if we have ball alive status (SciSports format)
    ball_alive = row.get("ball_alive")
    if ball_alive is not None:
        # Convert to boolean (1 = alive, 0 = dead)
        return BallState.ALIVE if float(ball_alive) == 1.0 else BallState.DEAD

    # Default to alive if no status information is available
    return BallState.ALIVE


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

    # Determine ball state from ball channel data
    ball_state = _determine_ball_state(row)

    frame = create_frame(
        frame_id=row["frame_id"],
        timestamp=timestamp,
        ball_owning_team=None,
        ball_state=ball_state,
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


def build_regex(
    data_format_specification,
    player_channels: List,
    sensors: List,
) -> str:
    """Build regex pattern for parsing EPTS data format."""
    player_channel_map = {
        player_channel.player_channel_id: player_channel
        for player_channel in player_channels
        if player_channel.channel.sensor in sensors
    }

    # Build ball channel map from all sensors that have ball data
    ball_channel_map = {}
    for sensor in sensors:
        if sensor.sensor_id in ["position", "height-estimator", "state"]:
            for channel in sensor.channels:
                ball_channel_map[channel.channel_id] = channel

    return data_format_specification.to_regex(
        player_channel_map=player_channel_map,
        ball_channel_map=ball_channel_map,
    )


def read_raw_data(
    raw_data: IO[bytes],
    metadata,
    sensor_ids: List[str] = None,
    sample_rate: float = 1.0,
    limit: int = 0,
) -> Iterator[dict]:
    """Read and parse EPTS tracking data from raw file."""
    sensors = [
        sensor
        for sensor in metadata.sensors
        if sensor_ids is None or sensor.sensor_id in sensor_ids
    ]

    data_specs = metadata.data_format_specifications

    current_data_spec_idx = 0
    end_frame_id = 0
    regex = None
    frame_name = "frameCount"

    def _set_current_data_spec(idx):
        nonlocal current_data_spec_idx, end_frame_id, regex, frame_name
        current_data_spec_idx = idx
        regex_str = build_regex(
            data_specs[current_data_spec_idx],
            metadata.player_channels,
            sensors,
        )

        end_frame_id = data_specs[current_data_spec_idx].end_frame
        regex = re.compile(regex_str)
        frame_name = (
            data_specs[current_data_spec_idx].split_register.children[0].name
        )

    _set_current_data_spec(0)

    periods = metadata.periods
    n = 0
    sample = 1.0 / sample_rate

    for i, line in enumerate(raw_data):
        if i % sample != 0:
            continue

        def to_float(v):
            return float(v) if v else float("nan")

        line = line.strip().decode("ascii")
        row = {
            k: to_float(v) for k, v in regex.search(line).groupdict().items()
        }
        frame_id = int(row[frame_name])
        if frame_id <= end_frame_id:
            timestamp = timedelta(seconds=frame_id / metadata.frame_rate)

            del row[frame_name]
            row["frame_id"] = frame_id
            row["timestamp"] = timestamp

            # Reset timestamp per period
            row["period_id"] = None
            for period in periods:
                if period.start_timestamp <= timestamp <= period.end_timestamp:
                    row["period_id"] = period.id
                    row["timestamp"] -= period.start_timestamp
                    break

            yield row

            n += 1
            if limit and n >= limit:
                break

        if frame_id >= end_frame_id:
            if current_data_spec_idx == len(data_specs) - 1:
                # don't know how to parse the rest of the file...
                break
            else:
                current_data_spec_idx += 1
                _set_current_data_spec(current_data_spec_idx)
