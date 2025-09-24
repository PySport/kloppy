from datetime import timedelta
from typing import IO, Dict, List, Optional, Tuple, Union

from lxml import objectify

from kloppy.domain import (
    AttackingDirection,
    DatasetFlag,
    Dimension,
    MetricPitchDimensions,
    Orientation,
    Period,
    PitchDimensions,
    Player,
    Provider,
    Score,
    Team,
    build_coordinate_system,
    Ground,
)
from kloppy.domain.models.position import PositionType

from ..metrica_epts.models import (
    DataFormatSpecification,
    EPTSMetadata,
    PlayerChannel,
    Sensor,
)


def _text(elm: Optional[object]) -> Optional[str]:
    return str(elm) if elm is not None else None


def _provider_value_map(value: str) -> str:
    return value


def _map_player_type(player_type: Optional[str]) -> PositionType:
    """Map SciSports player type to PositionType enum."""
    if not player_type:
        return PositionType.Unknown

    player_type_lower = player_type.lower()
    if "goalkeeper" in player_type_lower:
        return PositionType.Goalkeeper
    elif "field player" in player_type_lower:
        return PositionType.Unknown
    else:
        return PositionType.Unknown


def _load_provider_parameters(parent_elm) -> Dict:
    if parent_elm is None:
        return {}
    return {
        str(param.find("Name")): _text(param.find("Value"))
        for param in parent_elm.iterchildren(tag="ProviderParameter")
        if _text(param.find("Value")) is not None
    }


def _load_periods(metadata_elm) -> List[Period]:
    periods: List[Period] = []
    frame_rate = int(metadata_elm.find("GlobalConfig").find("FrameRate"))
    for session in metadata_elm.find("Sessions").iterchildren(tag="Session"):
        if _text(session.find("SessionType")) == "Period":
            params = _load_provider_parameters(
                session.find("ProviderSessionParameters")
            )
            if "Start Frame" in params and "End Frame" in params:
                start_frame = int(float(params["Start Frame"]))
                end_frame = int(float(params["End Frame"]))
                periods.append(
                    Period(
                        id=int(params.get("Label", len(periods) + 1)),
                        start_timestamp=timedelta(
                            seconds=start_frame / frame_rate
                        ),
                        end_timestamp=timedelta(
                            seconds=end_frame / frame_rate
                        ),
                    )
                )
    return periods


def _load_players(players_elm, team: Team) -> List[Player]:
    players: List[Player] = []
    for player_elm in players_elm.iterchildren(tag="Player"):
        if player_elm.attrib["teamId"] != team.team_id:
            continue

        # Load provider parameters to get player type
        attributes = _load_provider_parameters(
            player_elm.find("ProviderPlayerParameters")
        )

        # Map player type to PositionType
        player_type_str = attributes.get("PlayerType")
        position = _map_player_type(player_type_str)

        players.append(
            Player(
                team=team,
                jersey_no=int(player_elm.find("ShirtNumber")),
                player_id=player_elm.attrib["id"],
                name=_text(player_elm.find("Name")),
                starting=True,
                starting_position=position,
                attributes=attributes,
            )
        )
    return players


def _load_sensors(sensors_elm) -> List[Sensor]:
    return [
        Sensor.from_xml_element(sensor_elm)
        for sensor_elm in sensors_elm.iterchildren(tag="Sensor")
    ]


def _load_pitch_dimensions(
    metadata_elm, sensors: List[Sensor]
) -> Union[None, PitchDimensions]:
    # SciSports uses meters for x,y and provides Length/Width; return metric pitch dimensions
    sessions = metadata_elm.find("Sessions")
    session0 = sessions.find("Session") if sessions is not None else None
    field_size = (
        session0.find("MatchParameters").find("FieldSize")
        if session0 is not None
        else None
    )
    if field_size is None:
        return None
    length = float(field_size.find("Length"))
    width = float(field_size.find("Width"))
    return MetricPitchDimensions(
        x_dim=Dimension(0, length),
        y_dim=Dimension(0, width),
        pitch_length=length,
        pitch_width=width,
        standardized=False,
    )


def _parse_provider(provider_name: Optional[str]) -> Optional[Provider]:
    if not provider_name:
        return None
    name = provider_name.lower()
    if "scisports" in name:
        return Provider.SCISPORTS
    return Provider.OTHER


def load_metadata(
    metadata_file: IO[bytes], provider: Optional[Provider] = None
) -> EPTSMetadata:
    root = objectify.fromstring(metadata_file.read())
    metadata = root.find("Metadata")

    frame_rate = int(metadata.find("GlobalConfig").find("FrameRate"))

    # Teams and score
    team_name_map: Dict[str, str] = {
        team.attrib["id"]: str(team.find("Name"))
        for team in metadata.find("Teams").iterchildren(tag="Team")
    }
    # Determine home/away from ProviderTeamParameters Side
    ground_map: Dict[str, Ground] = {}
    for team in metadata.find("Teams").iterchildren(tag="Team"):
        params = _load_provider_parameters(team.find("ProviderTeamParameters"))
        side = params.get("Side", "H")
        ground = Ground.HOME if side == "H" else Ground.AWAY
        ground_map[team.attrib["id"]] = ground

    teams_metadata: Dict[Ground, Team] = {}
    for team_id, ground in ground_map.items():
        team = Team(
            team_id=team_id, name=team_name_map[team_id], ground=ground
        )
        team.players = _load_players(metadata.find("Players"), team)
        teams_metadata[ground] = team

    sensors = _load_sensors(
        metadata.find("Devices").find("Device").find("Sensors")
    )

    channel_map = {
        channel.channel_id: channel
        for sensor in sensors
        for channel in sensor.channels
    }

    all_players = [p for t in teams_metadata.values() for p in t.players]
    player_map = {p.player_id: p for p in all_players}

    player_channels: List[PlayerChannel] = [
        PlayerChannel(
            player_channel_id=elm.attrib["id"],
            player=player_map[elm.attrib["playerId"]],
            channel=channel_map[elm.attrib["channelId"]],
        )
        for elm in metadata.find("PlayerChannels").iterchildren(
            tag="PlayerChannel"
        )
    ]

    data_format_specifications = [
        DataFormatSpecification.from_xml_element(elm)
        for elm in root.find("DataFormatSpecifications").iterchildren(
            tag="DataFormatSpecification"
        )
    ]

    pitch_dimensions = _load_pitch_dimensions(metadata, sensors)
    periods = _load_periods(metadata)

    provider_name = _text(metadata.find("GlobalConfig").find("ProviderName"))
    provider = provider or _parse_provider(provider_name)

    # No coordinate system mapping defined for SciSports; leave None
    from_coordinate_system = None

    score = Score(home=0, away=0)

    return EPTSMetadata(
        teams=list(teams_metadata.values()),
        periods=periods,
        pitch_dimensions=pitch_dimensions,
        data_format_specifications=data_format_specifications,
        player_channels=player_channels,
        frame_rate=frame_rate,
        sensors=sensors,
        score=score,
        orientation=None,  # Will be determined from data in deserializer
        provider=provider,
        flags=~DatasetFlag.BALL_OWNING_TEAM,
        coordinate_system=from_coordinate_system,
    )
