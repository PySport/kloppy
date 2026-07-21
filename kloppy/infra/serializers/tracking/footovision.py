from datetime import datetime, timedelta
import json
import logging
from typing import IO, NamedTuple, Optional, Union

import pandas as pd

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
    KloppyCoordinateSystem,
    Official,
    OfficialType,
    Score,
)
from kloppy.domain.models.formation import FormationType
from kloppy.domain.models.time import Time, TimeContainer
from kloppy.domain.services.frame_factory import create_frame
from kloppy.infra.serializers.tracking.deserializer import (
    TrackingDataDeserializer,
)
from kloppy.utils import performance_logging

position_types_mapping: dict[str, PositionType] = {
    "GOALKEEPER": PositionType.Goalkeeper,
    "CENTRE_BACK_RIGHT": PositionType.RightCenterBack,
    "CENTRE_BACK_LEFT": PositionType.LeftCenterBack,
    "FULL_BACK_LEFT": PositionType.LeftBack,
    "FULL_BACK_RIGHT": PositionType.RightBack,
    "DEFENSIVE_MIDFIELDER": PositionType.DefensiveMidfield,
    "DEFENSIVE_MIDFIELDER_RIGHT": PositionType.RightDefensiveMidfield,
    "DEFENSIVE_MIDFIELDER_LEFT": PositionType.LeftDefensiveMidfield,
    "CENTRAL_MIDFIELDER_LEFT": PositionType.LeftCentralMidfield,
    "CENTRAL_MIDFIELDER_RIGHT": PositionType.RightCentralMidfield,
    "ATTACKING_MIDFIELDER_LEFT": PositionType.LeftAttackingMidfield,
    "ATTACKING_MIDFIELDER_RIGHT": PositionType.RightAttackingMidfield,
    "OFFENSIVE_MIDFIELDER": PositionType.AttackingMidfield,
    "WINGBACK_RIGHT": PositionType.RightWingBack,
    "WINGBACK_LEFT": PositionType.LeftWingBack,
    "STRIKER": PositionType.Striker,
    "STRIKER_RIGHT": PositionType.RightForward,
    "STRIKER_LEFT": PositionType.LeftForward,
}

formation_ids_mapping: dict[str, FormationType] = {
    # Footovision formation IDs
    "3-1-4-2": FormationType.THREE_ONE_FOUR_TWO,
    "3-2-4-1": FormationType.THREE_TWO_FOUR_ONE,
    "3-3-3-1": FormationType.THREE_THREE_THREE_ONE,
    "3-4-1-2": FormationType.THREE_FOUR_ONE_TWO,
    "3-4-2-1": FormationType.THREE_FOUR_TWO_ONE,
    "3-4-3": FormationType.THREE_FOUR_THREE,
    "3-4-3d": FormationType.THREE_FOUR_THREE_DIAMOND,
    "3-5-1-1": FormationType.THREE_FIVE_ONE_ONE,
    "3-5-2": FormationType.THREE_FIVE_TWO,
    "4-1-2-1-2": FormationType.FOUR_ONE_TWO_ONE_TWO,
    "4-1-3-2": FormationType.FOUR_ONE_THREE_TWO,
    "4-1-4-1": FormationType.FOUR_ONE_FOUR_ONE,
    "4-2-1-3": FormationType.FOUR_TWO_ONE_THREE,
    "4-2-2-2": FormationType.FOUR_TWO_TWO_TWO,
    "4-2-3-1": FormationType.FOUR_TWO_THREE_ONE,
    "4-2-4-0": FormationType.FOUR_TWO_FOUR_ZERO,
    "4-3-1-2": FormationType.FOUR_THREE_ONE_TWO,
    "4-3-2-1": FormationType.FOUR_THREE_TWO_ONE,
    "4-3-3": FormationType.FOUR_THREE_THREE,
    "4-4-1-1": FormationType.FOUR_FOUR_ONE_ONE,
    "4-4-2": FormationType.FOUR_FOUR_TWO,
    "4-5-1": FormationType.FOUR_FIVE_ONE,
    "5-3-2": FormationType.FIVE_THREE_TWO,
    "5-4-1": FormationType.FIVE_FOUR_ONE,
}

logger = logging.getLogger(__name__)

METERS_PER_YARD = 0.9144
FOOTOVISION_FPS = 25


def _provider_id(value) -> str:
    """Return provider identifiers in the format used by metadata."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class FootovisionTrackingInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_frames: IO[bytes]


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
        super().__init__(limit, sample_rate, coordinate_system)
        self.only_alive = only_alive

    @property
    def provider(self) -> Provider:
        return Provider.FOOTOVISION

    def deserialize(self, inputs: FootovisionTrackingInputs) -> TrackingDataset:
        with performance_logging("load data", logger=logger):
            raw_frames = json.load(inputs.raw_frames)
            meta_data = json.load(inputs.meta_data)

            df_frames_players = pd.DataFrame(raw_frames["players"])
            df_frames_ball = pd.DataFrame(raw_frames["ball"])

        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(df_frames_players)

        with performance_logging("parse teams ans players", logger=logger):
            teams = self.create_teams_and_players(meta_data, periods)

        transformer = self.get_transformer(pitch_length=meta_data["pitchLength"], pitch_width=meta_data["pitchWidth"], provider=self.provider)

        with performance_logging("parse tracking data", logger=logger):
            frames = []
            players_by_id = {
                player.player_id: player
                for team in teams
                for player in team.players
            }
            teams_by_id = {team.team_id: team for team in teams}
            ball_by_period_and_time = {
                (int(ball["halftime"]), float(ball["time"])): ball
                for ball in df_frames_ball.to_dict("records")
            }

            periods_by_id = {period.id: period for period in periods}
            sample = 1.0 / self.sample_rate

            # A provider frame is represented by one row per player. Group the
            # rows by halftime and timestamp to create Kloppy frames.
            grouped_players = df_frames_players.groupby(
                ["halftime", "time"], sort=True
            )
            for source_frame_id, ((period_id, time), player_rows) in enumerate(
                grouped_players
            ):
                if source_frame_id % sample != 0:
                    continue

                period_id = int(str(period_id))
                period = periods_by_id.get(period_id)
                if period is None:
                    continue

                players_data = {}
                for raw_player in player_rows.to_dict("records"):
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

                ball = ball_by_period_and_time.get((period_id, float(str(time))))
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
                    timestamp=timedelta(milliseconds=float(str(time))),
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
        
        pitch_length_m = meta_data["pitchLength"] * METERS_PER_YARD
        pitch_width_m = meta_data["pitchWidth"] * METERS_PER_YARD

        coordinate_system = KloppyCoordinateSystem(
            pitch_length_m,
            pitch_width_m,
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

        metadata = Metadata(
            teams=teams,
            periods=periods,
            coordinate_system=coordinate_system,
            pitch_dimensions=coordinate_system.pitch_dimensions,
            flags=DatasetFlag(0),
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
                    "unit": "yards",
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
        return TrackingDataset(records=frames, metadata=metadata)

    def create_periods(self, df_tracking):
        period_ids = sorted(df_tracking["halftime"].unique())
        periods = []

        for period_id in period_ids:
            frames = df_tracking[df_tracking["halftime"] == period_id]

            start_time = frames["time"].min()
            end_time = frames["time"].max()

            period = Period(
                id=int(period_id),
                start_timestamp=timedelta(milliseconds=float(start_time)),
                end_timestamp=timedelta(milliseconds=float(end_time)),
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
                timestamp=timedelta(
                    milliseconds=formation["time"]
                ),
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
