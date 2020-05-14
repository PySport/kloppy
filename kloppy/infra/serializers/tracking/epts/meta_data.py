from lxml import objectify

from kloppy.domain import Period
from kloppy.infra.utils import Readable

from .models import *


def _parse_periods(global_config_elm, frame_rate: int) -> List[Period]:
    provider_params = {
        str(param.find('Name')): int(param.find('Value'))
        for param in global_config_elm.iterchildren('ProviderGlobalParameters')
        if str(param.find('Value')) != ''
    }

    period_names = ['first_half', 'second_half', 'first_extra_half', 'second_extra_half']

    periods = []

    for idx, period_name in enumerate(period_names):
        start_key = f"{period_name}_start"
        end_key = f"{period_name}_end"
        if start_key in provider_params:
            periods.append(
                Period(
                    id=idx + 1,
                    start_timestamp=float(provider_params[start_key]) / frame_rate,
                    end_timestamp=float(provider_params[end_key]) / frame_rate
                )
            )
        else:
            # done
            break

    return periods


def _load_players(players_elm, team_map: Dict[str, Team]) -> List[Player]:
    return [
        Player(
            team=team_map[player_elm.attrib['teamId']],
            jersey_no=str(player_elm.find('ShirtNumber')),
            player_id=player_elm.attrib['id'],
            name=str(player_elm.find('Name'))
        )
        for player_elm in players_elm.iterchildren(tag='Player')
    ]


def _load_data_format_specifications(data_format_specifications_elm) -> List[DataFormatSpecification]:
    return [
        DataFormatSpecification.from_xml_element(data_format_specification_elm)
        for data_format_specification_elm
        in data_format_specifications_elm.iterchildren(tag='DataFormatSpecification')
    ]


def _load_sensors(sensors_elm) -> List[Sensor]:
    return [
        Sensor.from_xml_element(sensor_elm)
        for sensor_elm
        in sensors_elm.iterchildren(tag="Sensor")
    ]


def load_meta_data(meta_data_file: Readable) -> EPTSMetaData:
    root = objectify.fromstring(meta_data_file.read())
    meta_data = root.find('Metadata')

    score_path = objectify.ObjectPath("Metadata.Sessions.Session[0].MatchParameters.Score")
    score_elm = score_path.find(meta_data)
    _team_map = {
        score_elm.attrib['idLocalTeam']: Team.HOME,
        score_elm.attrib['idVisitingTeam']: Team.AWAY
    }

    players = _load_players(meta_data.find('Players'), _team_map)
    data_format_specifications = _load_data_format_specifications(root.find('DataFormatSpecifications'))

    device_path = objectify.ObjectPath("Metadata.Devices.Device[0].Sensors")
    sensors = _load_sensors(device_path.find(meta_data))

    _channel_map = {
        channel.channel_id: channel
        for sensor in sensors
        for channel in sensor.channels
    }

    _player_map = {
        player.player_id: player for player in players
    }
    
    player_channels = [
        PlayerChannel(
            player_channel_id=player_channel_elm.attrib['id'],
            player=_player_map[player_channel_elm.attrib['playerId']],
            channel=_channel_map[player_channel_elm.attrib['channelId']]
        )
        for player_channel_elm in meta_data.find('PlayerChannels').iterchildren(tag='PlayerChannel')
    ]

    team_name_map = {
        _team_map[team_elm.attrib['id']]: str(team_elm.find('Name'))
        for team_elm
        in meta_data.find('Teams').iterchildren(tag='Team')
    }

    frame_rate = int(meta_data.find('GlobalConfig').find('FrameRate'))
    periods = _parse_periods(meta_data.find('GlobalConfig'), frame_rate)

    return EPTSMetaData(
        home_team_name=team_name_map[Team.HOME],
        away_team_name=team_name_map[Team.AWAY],
        players=players,
        periods=periods,

        data_format_specifications=data_format_specifications,
        player_channels=player_channels,
        frame_rate=frame_rate,
        sensors=sensors
    )