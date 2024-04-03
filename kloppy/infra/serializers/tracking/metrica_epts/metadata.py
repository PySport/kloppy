from typing import IO
from datetime import timedelta

from lxml import objectify
import warnings

from kloppy.domain import (
    Period,
    PitchDimensions,
    Dimension,
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


def _load_periods(
    metadata_elm, team_map: dict, frame_rate: int
) -> List[Period]:
    global_config_elm = metadata_elm.find("GlobalConfig")
    provider_params = _load_provider_parameters(
        global_config_elm.find("ProviderGlobalParameters")
    )

    provider_teams_params = {
        team_map[team_elm.attrib["id"]]: _load_provider_parameters(
            team_elm.find("ProviderTeamsParameters")
        )
        for team_elm in metadata_elm.find("Teams").iterchildren(tag="Team")
    }

    period_names = [
        "first_half",
        "second_half",
        "first_extra_half",
        "second_extra_half",
    ]

    periods = []
    start_attacking_direction = AttackingDirection.NOT_SET

    for idx, period_name in enumerate(period_names):
        # the attacking direction is only defined for the first period
        # and alternates between periods
        if idx == 0:
            if (
                provider_teams_params[Ground.HOME].get(
                    "attack_direction_first_half"
                )
                == "left_to_right"
            ):
                start_attacking_direction = AttackingDirection.LTR
            elif (
                provider_teams_params[Ground.HOME].get(
                    "attack_direction_first_half"
                )
                == "right_to_left"
            ):
                start_attacking_direction = AttackingDirection.RTL

        start_key = f"{period_name}_start"
        end_key = f"{period_name}_end"
        if start_key in provider_params:
            periods.append(
                Period(
                    id=idx + 1,
                    start_timestamp=timedelta(
                        seconds=float(provider_params[start_key]) / frame_rate
                    ),
                    end_timestamp=timedelta(
                        seconds=float(provider_params[end_key]) / frame_rate
                    ),
                )
            )
        else:
            # done
            break

    return periods, start_attacking_direction


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

    if field_size_elm is not None and normalized:
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
    metadata_file: IO[bytes], provider: Provider = None
) -> EPTSMetadata:
    root = objectify.fromstring(metadata_file.read())
    metadata = root.find("Metadata")

    provider = _load_provider(metadata, provider)

    score_path = objectify.ObjectPath(
        "Metadata.Sessions.Session[0].MatchParameters.Score"
    )

    _team_name_map = {
        team_elm.attrib["id"]: str(team_elm.find("Name"))
        for team_elm in metadata.find("Teams").iterchildren(tag="Team")
    }

    if score_path.hasattr(metadata):
        score_elm = score_path.find(metadata)
        score = Score(
            home=score_elm.LocalTeamScore, away=score_elm.VisitingTeamScore
        )

        _team_map = {
            score_elm.attrib["idLocalTeam"]: Ground.HOME,
            score_elm.attrib["idVisitingTeam"]: Ground.AWAY,
        }
    else:
        score = Score(home=0, away=0)
        home_team_id, away_team_id = list(_team_name_map.keys())
        _team_map = {
            home_team_id: Ground.HOME,
            away_team_id: Ground.AWAY,
        }

    teams_metadata = {}
    for team_id, ground in _team_map.items():
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
    periods, start_attacking_direction = _load_periods(
        metadata, _team_map, frame_rate
    )

    if start_attacking_direction != AttackingDirection.NOT_SET:
        orientation = (
            Orientation.HOME_AWAY
            if start_attacking_direction == AttackingDirection.LTR
            else Orientation.AWAY_HOME
        )
    else:
        warnings.warn(
            "Could not determine orientation of dataset, defaulting to NOT_SET"
        )
        orientation = Orientation.NOT_SET

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
        orientation=orientation,
        provider=provider,
        flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
        coordinate_system=from_coordinate_system,
    )
