import re
from typing import List, Tuple, Set, Iterator

from kloppy.utils import Readable

from .models import (
    PlayerChannel,
    DataFormatSpecification,
    EPTSMetadata,
    Channel,
    Sensor,
)


def build_regex(
    data_format_specification: DataFormatSpecification,
    player_channels: List[PlayerChannel],
    sensors: List[Sensor],
) -> str:
    player_channel_map = {
        player_channel.player_channel_id: player_channel
        for player_channel in player_channels
        if player_channel.channel.sensor in sensors
    }

    position_sensor = None
    for sensor in sensors:
        if sensor.sensor_id == "position":
            position_sensor = sensor

    return data_format_specification.to_regex(
        player_channel_map=player_channel_map,
        ball_channel_map={
            channel.channel_id: channel for channel in position_sensor.channels
        }
        if position_sensor
        else {},
    )


def read_raw_data(
    raw_data: Readable,
    metadata: EPTSMetadata,
    sensor_ids: List[str] = None,
    sample_rate: float = 1.0,
    limit: int = 0,
) -> Iterator[dict]:
    sensors = [
        sensor
        for sensor in metadata.sensors
        if sensor_ids is None or sensor.sensor_id in sensor_ids
    ]

    data_specs = metadata.data_format_specifications

    current_data_spec_idx = 0
    end_frame_id = 0
    regex = None

    def _set_current_data_spec(idx):
        nonlocal current_data_spec_idx, end_frame_id, regex
        current_data_spec_idx = idx
        regex_str = build_regex(
            data_specs[current_data_spec_idx],
            metadata.player_channels,
            sensors,
        )

        end_frame_id = data_specs[current_data_spec_idx].end_frame
        regex = re.compile(regex_str)

    _set_current_data_spec(0)

    periods = metadata.periods
    n = 0
    sample = 1.0 / sample_rate

    for i, line in enumerate(raw_data):
        if i % sample != 0:
            continue

        line = line.strip().decode("ascii")
        row = {k: float(v) for k, v in regex.search(line).groupdict().items()}
        frame_id = int(row["frameCount"])
        if frame_id <= end_frame_id:
            timestamp = frame_id / metadata.frame_rate

            del row["frameCount"]
            row["frame_id"] = frame_id
            row["timestamp"] = timestamp

            row["period_id"] = None
            for period in periods:
                if period.start_timestamp <= timestamp <= period.end_timestamp:
                    row["period_id"] = period.id
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
