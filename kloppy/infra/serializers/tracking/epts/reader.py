from typing import List

from pandas import DataFrame

from kloppy.infra.utils import Readable

from .models import PlayerChannel, DataFormatSpecification


def build_regex(data_format_specification: DataFormatSpecification, player_channels: List[PlayerChannel]) -> str:
    player_channel_map = {
        player_channel.player_channel_id: player_channel
        for player_channel in player_channels
    }
    return data_format_specification.to_regex(
        player_channel_map=player_channel_map
    )


# def read(raw_data: Readable, meta_data: EPTSMetaData) -> DataFrame:
#
#
#     data_specs[0].split_register.to_regex(
#         player_channel_map=player_channel_map
#     )
#
