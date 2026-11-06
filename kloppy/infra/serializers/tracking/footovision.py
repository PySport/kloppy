from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
import json
import logging
import math
from typing import (
    IO,
    Any,
    NamedTuple,
    Optional,
    TypedDict,
    Union,
    cast,
)

from kloppy.domain import (
    BallState,
    DatasetFlag,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    PlayerData,
    Point,
    PositionType,
    Provider,
    Team,
    TrackingDataset,
)
from kloppy.domain.models.common import (
    Official,
    OfficialType,
    Score,
)
from kloppy.domain.models.formation import FormationType
from kloppy.domain.models.time import Time, TimeContainer
from kloppy.domain.services.frame_factory import create_frame
from kloppy.infra.serializers.event.footovision.mappings import (
    formation_ids_mapping,
    position_types_mapping,
)
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

FOOTOVISION_FPS = 25


class _FootovisionPlayerRecordRequired(TypedDict):
    playerId: int
    teamId: int
    halftime: int
    time: int
    x: float
    y: float
    speed: float


class FootovisionPlayerRecord(_FootovisionPlayerRecordRequired, total=False):
    accel: float
    line: str
    isObs: bool


class FootovisionBallRecord(TypedDict):
    halftime: int
    time: int
    x: float
    y: float
    speed: float
    teamIdWithBall: Optional[int]


class FootovisionTrackingRawData(TypedDict):
    players: list[FootovisionPlayerRecord]
    ball: list[FootovisionBallRecord]


def _provider_id(value) -> str:
    """Return provider identifiers in the format used by metadata."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Expected {context} to be an object.")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Expected {context} to be a list.")
    return value


def _require_value(record: Mapping[str, Any], field: str, context: str) -> Any:
    if field not in record or record[field] is None:
        raise ValueError(f"Missing required field '{field}' in {context}.")
    return record[field]


def _require_number(
    record: Mapping[str, Any], field: str, context: str
) -> None:
    value = _require_value(record, field, context)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected '{field}' in {context} to be numeric.")
    if not math.isfinite(value):
        raise ValueError(f"Expected '{field}' in {context} to be finite.")


def _require_non_negative_integer(
    record: Mapping[str, Any], field: str, context: str
) -> None:
    value = _require_value(record, field, context)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Expected '{field}' in {context} to be an integer.")
    if value < 0:
        raise ValueError(f"Expected '{field}' in {context} to be non-negative.")


def _validate_team(team_data: Any, context: str) -> None:
    team = _require_mapping(team_data, context)
    _require_value(team, "fullName", context)
    identifiers = _require_mapping(
        _require_value(team, "id", context), f"{context}.id"
    )
    _require_value(identifiers, "footovision", f"{context}.id")


def _validate_lineup(lineup_data: Any, context: str) -> None:
    for index, raw_player in enumerate(_require_list(lineup_data, context)):
        player_context = f"{context}[{index}]"
        player = _require_mapping(raw_player, player_context)
        _require_value(player, "usualName", player_context)
        _require_number(player, "shirtNumber", player_context)
        _require_value(player, "isStarter", player_context)
        identifiers = _require_mapping(
            _require_value(player, "playerId", player_context),
            f"{player_context}.playerId",
        )
        _require_value(identifiers, "footovision", f"{player_context}.playerId")


def _validate_formations(formations_data: Any, context: str) -> None:
    for index, raw_formation in enumerate(
        _require_list(formations_data, context)
    ):
        formation_context = f"{context}[{index}]"
        formation = _require_mapping(raw_formation, formation_context)
        _require_non_negative_integer(formation, "halftime", formation_context)
        _require_non_negative_integer(formation, "time", formation_context)
        _require_value(formation, "system", formation_context)


def _validate_tracking_inputs(
    raw_data: Any, meta_data: Any
) -> FootovisionTrackingRawData:
    raw_tracking = _require_mapping(raw_data, "tracking data")
    metadata = _require_mapping(meta_data, "match metadata")

    for field in (
        "id",
        "pitchLength",
        "pitchWidth",
        "isAttackingLeftToRightTeamId",
        "homeScore",
        "awayScore",
    ):
        _require_value(metadata, field, "match metadata")
    for field in ("pitchLength", "pitchWidth", "homeScore", "awayScore"):
        _require_number(metadata, field, "match metadata")

    for side in ("home", "away"):
        _validate_team(metadata.get(f"{side}Team"), f"{side}Team")
        _validate_lineup(
            metadata.get(f"{side}TeamLineups"), f"{side}TeamLineups"
        )
        _validate_formations(
            metadata.get(f"{side}TeamFormations"),
            f"{side}TeamFormations",
        )

    player_records = _require_list(raw_tracking.get("players"), "players")
    ball_records = _require_list(raw_tracking.get("ball"), "ball")
    for records, context, fields in (
        (
            player_records,
            "players",
            ("playerId", "teamId", "halftime", "time", "x", "y", "speed"),
        ),
        (
            ball_records,
            "ball",
            ("halftime", "time", "x", "y", "speed"),
        ),
    ):
        for index, raw_record in enumerate(records):
            record_context = f"{context}[{index}]"
            record = _require_mapping(raw_record, record_context)
            for field in fields:
                _require_number(record, field, record_context)
            for field in ("halftime", "time"):
                _require_non_negative_integer(record, field, record_context)

    for index, raw_ball in enumerate(ball_records):
        ball = _require_mapping(raw_ball, f"ball[{index}]")
        if "teamIdWithBall" not in ball:
            raise ValueError(
                f"Missing required field 'teamIdWithBall' in ball[{index}]."
            )

    return cast(FootovisionTrackingRawData, raw_tracking)


class FootovisionTrackingInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_frames: IO[bytes]


class _FootovisionTrackingDataset(TrackingDataset):
    """Preserve position histories supplied by Footovision."""

    def _init_player_positions(self):
        for team in self.metadata.teams:
            for player in team.players:
                if player.positions.items:
                    continue

                if player.starting:
                    player.set_position(
                        self.metadata.periods[0].start_time,
                        player.starting_position or PositionType.unknown(),
                    )


class FootovisionTrackingDeserializer(
    TrackingDataDeserializer[FootovisionTrackingInputs]
):
    def __init__(
        self,
        limit: Optional[int] = None,
        sample_rate: Optional[float] = None,
        coordinate_system: Optional[Union[str, Provider]] = None,
        only_alive: bool = False,
    ):
        if sample_rate is not None and not 0 < sample_rate <= 1:
            raise ValueError(
                "sample_rate must be greater than 0 and at most 1."
            )
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    @property
    def provider(self) -> Provider:
        return Provider.FOOTOVISION

    @staticmethod
    def _should_sample_frame(source_frame_id: int, sample_rate: float) -> bool:
        """Select frames at an approximately constant rate, including the first."""
        if source_frame_id == 0:
            return True
        return math.floor(source_frame_id * sample_rate) > math.floor(
            (source_frame_id - 1) * sample_rate
        )

    def deserialize(self, inputs: FootovisionTrackingInputs) -> TrackingDataset:
        with performance_logging("load data", logger=logger):
            raw_frames = json.load(inputs.raw_frames)
            meta_data = json.load(inputs.meta_data)
            raw_frames = _validate_tracking_inputs(raw_frames, meta_data)
            raw_players = raw_frames["players"]
            raw_ball = raw_frames["ball"]

        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_players, raw_ball)

        with performance_logging("parse teams ans players", logger=logger):
            teams = self.create_teams_and_players(meta_data, periods)

        # Pitch dimensions are already metres; coordinates stay normalized 0..1.
        transformer = self.get_transformer(
            pitch_length=meta_data["pitchLength"],
            pitch_width=meta_data["pitchWidth"],
            provider=self.provider,
        )

        with performance_logging("parse tracking data", logger=logger):
            frames = []
            players_by_id = {
                player.player_id: player
                for team in teams
                for player in team.players
            }
            teams_by_id = {team.team_id: team for team in teams}
            ball_by_period_and_time: dict[
                tuple[int, int], FootovisionBallRecord
            ] = {}
            for ball in raw_ball:
                key = (ball["halftime"], ball["time"])
                if key in ball_by_period_and_time:
                    raise ValueError(
                        "Multiple ball records found for "
                        f"halftime={key[0]}, time={key[1]}."
                    )
                ball_by_period_and_time[key] = ball

            players_by_period_and_time: defaultdict[
                tuple[int, int], list[FootovisionPlayerRecord]
            ] = defaultdict(list)
            player_ids_by_period_and_time: set[tuple[int, int, str]] = set()
            for raw_player in raw_players:
                key = (raw_player["halftime"], raw_player["time"])
                player_key = (
                    *key,
                    str(raw_player["playerId"]),
                )
                if player_key in player_ids_by_period_and_time:
                    raise ValueError(
                        "Multiple player records found for "
                        f"player={player_key[2]}, halftime={key[0]}, time={key[1]}."
                    )
                player_ids_by_period_and_time.add(player_key)
                players_by_period_and_time[key].append(raw_player)

            periods_by_id = {period.id: period for period in periods}

            # Consider every timestamp represented in either feed so that
            # incomplete frames can be logged and skipped explicitly.
            frame_keys = sorted(
                set(players_by_period_and_time) | set(ball_by_period_and_time)
            )
            for source_frame_id, (period_id, time) in enumerate(frame_keys):
                if not self._should_sample_frame(
                    source_frame_id, self.sample_rate
                ):
                    continue

                period = periods_by_id.get(period_id)
                if period is None:
                    continue

                player_rows = players_by_period_and_time.get(
                    (period_id, time), []
                )
                if not player_rows:
                    logger.warning(
                        "Skipping frame with no player tracking data for "
                        "halftime=%s, time=%s.",
                        period_id,
                        time,
                    )
                    continue

                players_data = {}
                for raw_player in player_rows:
                    player = players_by_id.get(str(raw_player["playerId"]))
                    if player is None:
                        logger.warning(
                            "Skipping tracking data for unknown player %s",
                            raw_player["playerId"],
                        )
                        continue

                    players_data[player] = PlayerData(
                        coordinates=Point(
                            x=float(raw_player["x"]),
                            y=float(raw_player["y"]),
                        ),
                        speed=float(raw_player["speed"]),
                        other_data={
                            "acceleration": raw_player.get("accel"),
                            "line": raw_player.get("line"),
                        },
                    )

                if not players_data:
                    logger.warning(
                        "Skipping frame with no recognized player tracking "
                        "data for halftime=%s, time=%s.",
                        period_id,
                        time,
                    )
                    continue

                ball = ball_by_period_and_time.get((period_id, time))
                if ball is None:
                    logger.warning(
                        "Skipping frame with no ball tracking data for "
                        "halftime=%s, time=%s.",
                        period_id,
                        time,
                    )
                    continue
                ball_owning_team = (
                    teams_by_id.get(_provider_id(ball["teamIdWithBall"]))
                    if ball and ball.get("teamIdWithBall") is not None
                    else None
                )
                ball_coordinates = (
                    Point(x=float(ball["x"]), y=float(ball["y"]))
                    if ball is not None
                    else None
                )
                ball_state = (
                    BallState.ALIVE
                    if ball_owning_team is not None
                    else BallState.DEAD
                )

                if self.only_alive and ball_state == BallState.DEAD:
                    continue

                frame = create_frame(
                    frame_id=source_frame_id,
                    timestamp=timedelta(milliseconds=time),
                    ball_coordinates=ball_coordinates,
                    ball_speed=(
                        float(ball["speed"])
                        if ball is not None and ball.get("speed") is not None
                        else None
                    ),
                    ball_state=ball_state,
                    ball_owning_team=ball_owning_team,
                    players_data=players_data,
                    period=period,
                    other_data={},
                )
                frames.append(transformer.transform_frame(frame))

                if self.limit and len(frames) >= self.limit:
                    break

        home_team_id = str(meta_data["homeTeam"]["id"]["footovision"])
        away_team_id = str(meta_data["awayTeam"]["id"]["footovision"])
        first_half_ltr_team_id = str(meta_data["isAttackingLeftToRightTeamId"])

        if first_half_ltr_team_id == home_team_id:
            orientation = Orientation.HOME_AWAY
        elif first_half_ltr_team_id == away_team_id:
            orientation = Orientation.AWAY_HOME
        else:
            raise ValueError(
                "isAttackingLeftToRightTeamId does not match either match team."
            )

        referee = meta_data.get("referee")
        officials = []
        if referee and referee.get("id", {}).get("footovision") is not None:
            officials.append(
                Official(
                    official_id=str(referee["id"]["footovision"]),
                    name=referee.get("usualName"),
                    role=OfficialType.MainReferee,
                )
            )

        coordinate_system = transformer.get_to_coordinate_system()
        if coordinate_system is None:
            raise RuntimeError(
                "Footovision tracking transformer has no target coordinate system."
            )

        metadata = Metadata(
            teams=teams,
            periods=periods,
            coordinate_system=coordinate_system,
            pitch_dimensions=coordinate_system.pitch_dimensions,
            flags=DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM,
            provider=Provider.FOOTOVISION,
            orientation=orientation,
            game_id=str(meta_data["id"]),
            date=(
                datetime.fromisoformat(meta_data["date"].replace("Z", "+00:00"))
                if meta_data.get("date")
                else None
            ),
            game_week=(
                str(meta_data["matchday"])
                if meta_data.get("matchday") is not None
                else None
            ),
            score=Score(
                home=int(meta_data["homeScore"]),
                away=int(meta_data["awayScore"]),
            ),
            frame_rate=FOOTOVISION_FPS,
            officials=officials,
            attributes={
                "title": meta_data.get("title"),
                "competition": meta_data.get("competition"),
                "competition_id": meta_data.get("competitionId"),
                "season": meta_data.get("season"),
                "season_id": meta_data.get("seasonId"),
                "last_update": meta_data.get("lastUpdate"),
                "source_pitch_dimensions": {
                    "length": meta_data.get("pitchLength"),
                    "width": meta_data.get("pitchWidth"),
                    "unit": "meters",
                },
                "formation_changes": {
                    "home": [
                        {
                            "halftime": formation["halftime"],
                            "time": formation["time"],
                            "system": formation["system"],
                            "reason": formation.get("reasonForFormationChange"),
                            "on_field_player_positions": formation.get(
                                "onFieldPlayersPositions"
                            ),
                        }
                        for formation in meta_data["homeTeamFormations"]
                    ],
                    "away": [
                        {
                            "halftime": formation["halftime"],
                            "time": formation["time"],
                            "system": formation["system"],
                            "reason": formation.get("reasonForFormationChange"),
                            "on_field_player_positions": formation.get(
                                "onFieldPlayersPositions"
                            ),
                        }
                        for formation in meta_data["awayTeamFormations"]
                    ],
                },
                "teams": {
                    "home": {
                        "short_name": meta_data["homeTeam"].get("shortName"),
                        "country_id": meta_data["homeTeam"].get("countryId"),
                        "category": meta_data["homeTeam"].get("category"),
                        "is_national_team": meta_data["homeTeam"].get(
                            "isNationalTeam"
                        ),
                    },
                    "away": {
                        "short_name": meta_data["awayTeam"].get("shortName"),
                        "country_id": meta_data["awayTeam"].get("countryId"),
                        "category": meta_data["awayTeam"].get("category"),
                        "is_national_team": meta_data["awayTeam"].get(
                            "isNationalTeam"
                        ),
                    },
                },
            },
        )
        return _FootovisionTrackingDataset(records=frames, metadata=metadata)

    def create_periods(
        self,
        raw_players: Sequence[FootovisionPlayerRecord],
        raw_ball: Sequence[FootovisionBallRecord],
    ) -> list[Period]:
        timestamps_by_period: defaultdict[int, list[int]] = defaultdict(list)
        for records in (raw_players, raw_ball):
            for record in records:
                timestamps_by_period[record["halftime"]].append(record["time"])

        periods = []

        for period_id, timestamps in sorted(timestamps_by_period.items()):
            start_time = min(timestamps)
            if start_time != 0:
                raise ValueError(
                    f"Footovision period {period_id} must start at 0 ms; "
                    f"first timestamp is {start_time} ms."
                )
            end_time = max(timestamps)

            period = Period(
                id=period_id,
                start_timestamp=timedelta(0),
                end_timestamp=timedelta(milliseconds=end_time),
            )
            periods.append(period)

        for i, period in enumerate(periods):
            previous = periods[i - 1] if i else None
            following = periods[i + 1] if i + 1 < len(periods) else None
            period.set_refs(previous, following)

        return periods

    def create_teams_and_players(
        self,
        meta_data,
        periods: list[Period],
    ):
        periods_by_id = {period.id: period for period in periods}

        def get_formation_time(formation) -> Time:
            period_id = int(formation["halftime"])

            try:
                period = periods_by_id[period_id]
            except KeyError as exc:
                raise ValueError(
                    f"No Period found for halftime={period_id}"
                ) from exc

            return Time(
                period=period,
                timestamp=timedelta(milliseconds=formation["time"]),
            )

        def create_player(team, raw_player, formations):
            player_id = str(raw_player["playerId"]["footovision"])
            positions: TimeContainer[PositionType] = TimeContainer()

            for formation in formations:
                on_field_positions = (
                    formation.get("onFieldPlayersPositions") or {}
                )
                raw_position = on_field_positions.get(player_id)

                if raw_position is None:
                    continue

                positions.set(
                    time=get_formation_time(formation),
                    item=position_types_mapping.get(
                        raw_position,
                        PositionType.Unknown,
                    ),
                )

            return Player(
                player_id=player_id,
                team=team,
                name=raw_player["usualName"],
                jersey_no=int(raw_player["shirtNumber"]),
                starting=bool(raw_player["isStarter"]),
                starting_position=position_types_mapping.get(
                    raw_player.get("position"),
                    PositionType.Unknown,
                ),
                positions=positions,
                attributes={
                    "start_time": raw_player.get("startTime"),
                    "end_time": raw_player.get("endTime"),
                    "playing_time": raw_player.get("playingTime"),
                    "source_position": raw_player.get("position"),
                },
            )

        def create_team(team_data, lineup, ground, formations):
            formation_history: TimeContainer[FormationType] = TimeContainer()

            for formation in formations:
                formation_history.set(
                    time=get_formation_time(formation),
                    item=formation_ids_mapping.get(
                        formation.get("system"),
                        FormationType.UNKNOWN,
                    ),
                )

            starting_formation = (
                formation_ids_mapping.get(
                    formations[0].get("system"),
                    FormationType.UNKNOWN,
                )
                if formations
                else FormationType.UNKNOWN
            )

            team = Team(
                team_id=str(team_data["id"]["footovision"]),
                name=team_data["fullName"],
                ground=ground,
                starting_formation=starting_formation,
                formations=formation_history,
            )

            team.players = [
                create_player(team, raw_player, formations)
                for raw_player in lineup
            ]

            return team

        home_team = create_team(
            team_data=meta_data["homeTeam"],
            lineup=meta_data["homeTeamLineups"],
            ground=Ground.HOME,
            formations=meta_data["homeTeamFormations"],
        )

        away_team = create_team(
            team_data=meta_data["awayTeam"],
            lineup=meta_data["awayTeamLineups"],
            ground=Ground.AWAY,
            formations=meta_data["awayTeamFormations"],
        )

        return [home_team, away_team]
