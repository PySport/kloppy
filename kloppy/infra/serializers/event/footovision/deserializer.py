from datetime import datetime, timedelta
import json
import logging
from typing import IO, NamedTuple

from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    Ground,
    Metadata,
    Official,
    OfficialType,
    Orientation,
    Period,
    Player,
    PositionType,
    Provider,
    Score,
    Team,
)
from kloppy.domain.models.common import KloppyCoordinateSystem
from kloppy.domain.models.formation import FormationType
from kloppy.domain.models.time import Time, TimeContainer
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.infra.serializers.event.footovision.mappings import (
    formation_ids_mapping,
    position_types_mapping,
)
from kloppy.infra.serializers.event.footovision.specification import (
    create_footovision_events,
)
from kloppy.utils import performance_logging

METERS_PER_YARD = 0.9144
FOOTOVISION_FPS = 25

logger = logging.getLogger(__name__)


class FootovisionMetadata(NamedTuple):
    score: Score
    teams: list[Team]
    periods: list[Period]
    x_max: float
    y_max: float
    fps: int
    officials: list[Official]


class FootovisionEventDataInputs(NamedTuple):
    event_data: IO[bytes]
    meta_data: IO[bytes]


class FootovisionEventDataDeserializer(
    EventDataDeserializer[FootovisionEventDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.FOOTOVISION

    def _deserialize(self, inputs: FootovisionEventDataInputs) -> EventDataset:
        with performance_logging("load data", logger=logger):
            raw_events = json.load(inputs.event_data)
            meta_data = json.load(inputs.meta_data)

        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_events)

        with performance_logging("parse teams ans players", logger=logger):
            teams = self.create_teams_and_players(meta_data, periods)

        with performance_logging("parse events", logger=logger):
            events = []

            for footovision_event in create_footovision_events(
                raw_events, meta_data
            ):
                footovision_event.set_refs(periods, teams)

                events.extend(footovision_event.deserialize(self.event_factory))

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
        return EventDataset(
            metadata=metadata,
            records=events,
        )

    def create_periods(self, raw_events):
        periods: list[Period] = []

        for period_id in range(1, 6):
            events_halftime = [
                event for event in raw_events if event["halftime"] == period_id
            ]

            if not events_halftime:
                continue

            start_event = events_halftime[0]
            end_event = events_halftime[-1]

            period = Period(
                id=int(period_id),
                start_timestamp=timedelta(
                    milliseconds=start_event["startTime"]
                ),
                end_timestamp=timedelta(milliseconds=end_event["endTime"]),
            )

            periods.append(period)

        for i, period in enumerate(periods):
            prev_period = periods[i - 1] if i > 0 else None
            next_period = periods[i + 1] if i < len(periods) - 1 else None
            period.set_refs(prev_period, next_period)

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
