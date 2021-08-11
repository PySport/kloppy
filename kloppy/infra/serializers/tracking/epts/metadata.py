from lxml import objectify
import warnings

from kloppy.domain import (
    Period,
    PitchDimensions,
    Dimension,
    Team,
    Score,
    Ground,
    DatasetFlag,
    AttackingDirection,
    Orientation,
    Position,
    Point,
    Provider,
    build_coordinate_system,
)
from kloppy.utils import Readable

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
        global_config_elm.find("ProviderGlobalParameters")
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


def _load_players(players_elm, team: Team) -> List[Player]:
    return [
        Player(
            team=team,
            jersey_no=int(player_elm.find("ShirtNumber")),
            player_id=player_elm.attrib["id"],
            name=str(player_elm.find("Name")),
            position=_load_position_data(
                player_elm.find("ProviderPlayerParameters")
            ),
            attributes=_load_provider_parameters(
                player_elm.find("ProviderPlayerParameters")
            ),
        )
        for player_elm in players_elm.iterchildren(tag="Player")
        if player_elm.attrib["teamId"] == team.team_id
    ]


def _load_position_data(parent_elm) -> Position:
    # TODO: _load_provider_parameters is called twice to set position data
    # and then again to set the attributes. Also, data in position should not
    # be duplicated in attributes either.
    player_provider_parameters = _load_provider_parameters(parent_elm)
    if "position_index" not in player_provider_parameters:
        return None

    return Position(
        position_id=player_provider_parameters["position_index"],
        name=player_provider_parameters["position_type"],
        coordinates=Point(
            player_provider_parameters["position_x"],
            player_provider_parameters["position_y"],
        ),
    )


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
    metadata_elm, sensors: List[Sensor]
) -> Union[None, PitchDimensions]:

    normalized = False
    for sensor in sensors:
        if sensor.sensor_id == "position":
            if sensor.channels[0].unit == "normalized":
                normalized = True
                break

    field_size_path = objectify.ObjectPath("Metadata.Sessions.Session[0]")
    field_size_elm = field_size_path.find(metadata_elm).find("FieldSize")

    if field_size_elm and normalized:
        return PitchDimensions(
            x_dim=Dimension(0, 1),
            y_dim=Dimension(0, 1),
            length=int(field_size_elm.find("Width")),
            width=int(field_size_elm.find("Height")),
        )
    else:
        return None


def _parse_provider(provider_name: Union[str, None]) -> Provider:
    if provider_name:
        if provider_name == "Metrica Sports":
            return Provider.METRICA
        else:
            warnings.warn(
                "The Provider is not known to Kloppy.",
                Warning,
            )
    else:
        return None


def _load_provider(metadata_elm, provider: Provider = None) -> Provider:
    provider_path = objectify.ObjectPath("Metadata.GlobalConfig.ProviderName")
    provider_name = provider_path.find(metadata_elm)
    provider_from_file = _parse_provider(provider_name)
    if provider:
        if provider_from_file and provider_from_file != provider:
            warnings.warn(
                f"Given provider name is different to the name of the Provider read from the XML-file",
                Warning,
            )
    else:
        provider = provider_from_file
    return provider


def load_metadata(
    metadata_file: Readable, provider: Provider = None
) -> EPTSMetadata:
    root = objectify.fromstring(metadata_file.read())
    metadata = root.find("Metadata")

    provider = _load_provider(metadata, provider)

    score_path = objectify.ObjectPath(
        "Metadata.Sessions.Session[0].MatchParameters.Score"
    )
    score_elm = score_path.find(metadata)
    score = Score(
        home=score_elm.LocalTeamScore, away=score_elm.VisitingTeamScore
    )

    _team_map = {
        Ground.HOME: score_elm.attrib["idLocalTeam"],
        Ground.AWAY: score_elm.attrib["idVisitingTeam"],
    }

    _team_name_map = {
        team_elm.attrib["id"]: str(team_elm.find("Name"))
        for team_elm in metadata.find("Teams").iterchildren(tag="Team")
    }

    teams_metadata = {}
    for ground, team_id in _team_map.items():
        team = Team(
            team_id=team_id, name=_team_name_map[team_id], ground=ground
        )
        team.players = _load_players(metadata.find("Players"), team)
        teams_metadata.update({ground: team})

    data_format_specifications = _load_data_format_specifications(
        root.find("DataFormatSpecifications")
    )

    device_path = objectify.ObjectPath("Metadata.Devices.Device[0].Sensors")
    sensors = _load_sensors(device_path.find(metadata))

    _channel_map = {
        channel.channel_id: channel
        for sensor in sensors
        for channel in sensor.channels
    }

    _all_players = [
        player
        for key, value in teams_metadata.items()
        for player in value.players
    ]

    _player_map = {player.player_id: player for player in _all_players}

    player_channels = [
        PlayerChannel(
            player_channel_id=player_channel_elm.attrib["id"],
            player=_player_map[player_channel_elm.attrib["playerId"]],
            channel=_channel_map[player_channel_elm.attrib["channelId"]],
        )
        for player_channel_elm in metadata.find("PlayerChannels").iterchildren(
            tag="PlayerChannel"
        )
    ]

    frame_rate = int(metadata.find("GlobalConfig").find("FrameRate"))
    pitch_dimensions = _load_pitch_dimensions(metadata, sensors)
    periods = _load_periods(metadata.find("GlobalConfig"), frame_rate)

    if periods:
        start_attacking_direction = periods[0].attacking_direction
    else:
        start_attacking_direction = None

    orientation = (
        (
            Orientation.FIXED_HOME_AWAY
            if start_attacking_direction == AttackingDirection.HOME_AWAY
            else Orientation.FIXED_AWAY_HOME
        )
        if start_attacking_direction != AttackingDirection.NOT_SET
        else None
    )

    metadata.orientation = orientation

    if provider and pitch_dimensions:
        from_coordinate_system = build_coordinate_system(
            provider,
            length=pitch_dimensions.length,
            width=pitch_dimensions.width,
        )
    else:
        from_coordinate_system = None

    return EPTSMetadata(
        teams=list(teams_metadata.values()),
        periods=periods,
        pitch_dimensions=pitch_dimensions,
        data_format_specifications=data_format_specifications,
        player_channels=player_channels,
        frame_rate=frame_rate,
        sensors=sensors,
        score=score,
        orientation=None,
        provider=provider,
        flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
        coordinate_system=from_coordinate_system,
    )
