from lxml import objectify

from kloppy.domain import Period, PitchDimensions, Dimension
from kloppy.infra.utils import Readable

from .models import *


def noop(x):
    return x


def _load_provider_parameters(parent_elm, value_mapper=None) -> Dict:
    if parent_elm is None:
        return {}

    if not value_mapper:
        value_mapper = noop

    return {
        str(param.find("Name")): value_mapper(param.find("Value"))
        for param in parent_elm.iterchildren(tag="ProviderParameter")
        if param.find("Value") != ""
    }


def _load_periods(global_config_elm, frame_rate: int) -> List[Period]:
    provider_params = _load_provider_parameters(
        global_config_elm.find("ProviderGlobalParameters"), value_mapper=int
    )

    period_names = [
        "first_half",
        "second_half",
        "first_extra_half",
        "second_extra_half",
    ]

    periods = []

    for idx, period_name in enumerate(period_names):
        start_key = f"{period_name}_start"
        end_key = f"{period_name}_end"
        if start_key in provider_params:
            periods.append(
                Period(
                    id=idx + 1,
                    start_timestamp=float(provider_params[start_key])
                    / frame_rate,
                    end_timestamp=float(provider_params[end_key]) / frame_rate,
                )
            )
        else:
            # done
            break

    return periods


def _load_players(players_elm, team_map: Dict[str, Team]) -> List[Player]:
    return [
        Player(
            team=team_map[player_elm.attrib["teamId"]],
            jersey_no=str(player_elm.find("ShirtNumber")),
            player_id=player_elm.attrib["id"],
            name=str(player_elm.find("Name")),
            attributes=_load_provider_parameters(
                players_elm.find("ProviderPlayerParameters")
            ),
        )
        for player_elm in players_elm.iterchildren(tag="Player")
    ]


def _load_data_format_specifications(
    data_format_specifications_elm,
) -> List[DataFormatSpecification]:
    return [
        DataFormatSpecification.from_xml_element(data_format_specification_elm)
        for data_format_specification_elm in data_format_specifications_elm.iterchildren(
            tag="DataFormatSpecification"
        )
    ]


def _load_sensors(sensors_elm) -> List[Sensor]:
    return [
        Sensor.from_xml_element(sensor_elm)
        for sensor_elm in sensors_elm.iterchildren(tag="Sensor")
    ]


def _load_pitch_dimensions(
    meta_data_elm, sensors: List[Sensor]
) -> Union[None, PitchDimensions]:

    normalized = False
    for sensor in sensors:
        if sensor.sensor_id == "position":
            if sensor.channels[0].unit == "normalized":
                normalized = True
                break

    field_size_path = objectify.ObjectPath("Metadata.Sessions.Session[0]")
    field_size_elm = field_size_path.find(meta_data_elm).find("FieldSize")

    if field_size_elm is not None and normalized:
        return PitchDimensions(
            x_dim=Dimension(0, 1),
            y_dim=Dimension(0, 1),
            x_per_meter=1 / int(field_size_elm.find("Width")),
            y_per_meter=1 / int(field_size_elm.find("Height")),
        )
    else:
        return None


def load_meta_data(meta_data_file: Readable) -> EPTSMetaData:
    root = objectify.fromstring(meta_data_file.read())
    meta_data = root.find("Metadata")

    score_path = objectify.ObjectPath(
        "Metadata.Sessions.Session[0].MatchParameters.Score"
    )
    score_elm = score_path.find(meta_data)
    _team_map = {
        score_elm.attrib["idLocalTeam"]: Team.HOME,
        score_elm.attrib["idVisitingTeam"]: Team.AWAY,
    }

    players = _load_players(meta_data.find("Players"), _team_map)
    data_format_specifications = _load_data_format_specifications(
        root.find("DataFormatSpecifications")
    )

    device_path = objectify.ObjectPath("Metadata.Devices.Device[0].Sensors")
    sensors = _load_sensors(device_path.find(meta_data))

    _channel_map = {
        channel.channel_id: channel
        for sensor in sensors
        for channel in sensor.channels
    }

    _player_map = {player.player_id: player for player in players}

    player_channels = [
        PlayerChannel(
            player_channel_id=player_channel_elm.attrib["id"],
            player=_player_map[player_channel_elm.attrib["playerId"]],
            channel=_channel_map[player_channel_elm.attrib["channelId"]],
        )
        for player_channel_elm in meta_data.find(
            "PlayerChannels"
        ).iterchildren(tag="PlayerChannel")
    ]

    team_name_map = {
        _team_map[team_elm.attrib["id"]]: str(team_elm.find("Name"))
        for team_elm in meta_data.find("Teams").iterchildren(tag="Team")
    }

    frame_rate = int(meta_data.find("GlobalConfig").find("FrameRate"))
    periods = _load_periods(meta_data.find("GlobalConfig"), frame_rate)
    pitch_dimensions = _load_pitch_dimensions(meta_data, sensors)

    return EPTSMetaData(
        home_team_name=team_name_map[Team.HOME],
        away_team_name=team_name_map[Team.AWAY],
        players=players,
        periods=periods,
        pitch_dimensions=pitch_dimensions,
        data_format_specifications=data_format_specifications,
        player_channels=player_channels,
        frame_rate=frame_rate,
        sensors=sensors,
    )
