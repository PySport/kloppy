from typing import NamedTuple, IO, Optional
import logging
import json
from itertools import zip_longest

from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    FormationType,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    Position,
    Provider,
    Team,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging
from . import specification as SB
from .helpers import parse_freeze_frame, parse_str_ts

logger = logging.getLogger(__name__)


class StatsBombInputs(NamedTuple):
    event_data: IO[bytes]
    lineup_data: IO[bytes]
    three_sixty_data: Optional[IO[bytes]]


class StatsBombDeserializer(EventDataDeserializer[StatsBombInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.STATSBOMB

    def deserialize(self, inputs: StatsBombInputs) -> EventDataset:
        # Intialize coordinate system transformer
        self.transformer = self.get_transformer(length=120, width=80)

        # Load data from JSON files
        # and determine fidelity versions for x/y coordinates
        with performance_logging("load data", logger=logger):
            (
                raw_events,
                lineups,
                three_sixty_data,
                data_version,
            ) = self.load_data(inputs)
        logger.info(
            "determined fidelity versions (Shot v%d / XY v%d)",
            data_version.shot_fidelity_version,
            data_version.xy_fidelity_version,
        )

        # Create teams and players
        with performance_logging("parse teams ans players", logger=logger):
            teams = self.create_teams_and_players(raw_events, lineups)

        # Create periods
        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_events)

        # Create events
        with performance_logging("parse events", logger=logger):
            events = []
            for raw_event in raw_events.values():
                new_events = (
                    raw_event.set_version(data_version)
                    .set_refs(periods, teams, raw_events)
                    .deserialize(self.event_factory)
                )
                for event in new_events:
                    if self.should_include_event(event):
                        # Transform event to the coordinate system
                        event = self.transformer.transform_event(event)

                        # Add freeze_frame information
                        if "freeze_frame" in event.raw_event.get("shot", {}):
                            event.freeze_frame = self.transformer.transform_frame(
                                parse_freeze_frame(
                                    freeze_frame=event.raw_event["shot"][
                                        "freeze_frame"
                                    ],
                                    home_team=teams[0],
                                    away_team=teams[1],
                                    event=event,
                                    fidelity_version=data_version.shot_fidelity_version,
                                )
                            )

                        if (
                            not event.freeze_frame
                            and event.event_id in three_sixty_data
                        ):
                            freeze_frame = three_sixty_data[event.event_id]
                            event.freeze_frame = self.transformer.transform_frame(
                                parse_freeze_frame(
                                    freeze_frame=freeze_frame["freeze_frame"],
                                    home_team=teams[0],
                                    away_team=teams[1],
                                    event=event,
                                    fidelity_version=data_version.xy_fidelity_version,
                                    visible_area=freeze_frame["visible_area"],
                                )
                            )
                        events.append(event)

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=None,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            score=None,
            provider=Provider.STATSBOMB,
            coordinate_system=self.transformer.get_to_coordinate_system(),
        )
        return EventDataset(metadata=metadata, records=events)

    def load_data(self, inputs: StatsBombInputs):
        raw_events = {}
        shot_fidelity_version, xy_fidelity_version = 1, 1
        for event in json.load(inputs.event_data):
            # load the event
            raw_events[event["id"]] = SB.event_decoder(event)
            # determine the fidelity version
            if "location" in event:
                x, y, *_ = event["location"]
                # find out if x and y are integers disguised as floats
                if not (x.is_integer() and y.is_integer()):
                    event_type = SB.EVENT_TYPE(event["type"])
                    if event_type in (SB.EVENT_TYPE.SHOT,):
                        shot_fidelity_version = 2
                    elif event_type in (
                        SB.EVENT_TYPE.CARRY,
                        SB.EVENT_TYPE.DRIBBLE,
                        SB.EVENT_TYPE.PASS,
                    ):
                        xy_fidelity_version = 2

        version = SB.Version(
            shot_fidelity_version=shot_fidelity_version,
            xy_fidelity_version=xy_fidelity_version,
        )

        lineups = json.load(inputs.lineup_data)

        three_sixty_data = (
            {
                item["event_uuid"]: item
                for item in json.load(inputs.three_sixty_data)
            }
            if inputs.three_sixty_data
            else {}
        )

        return raw_events, lineups, three_sixty_data, version

    def create_teams_and_players(self, raw_events, lineups):
        it_events = iter(raw_events.values())
        starting_xi_events = [
            next(it_events).raw_event,
            next(it_events).raw_event,
        ]

        # Determine home and away lineups
        home_lineup, away_lineup = (
            lineups
            if starting_xi_events[0]["team"]["id"] == lineups[0]["team_id"]
            else reversed(lineups)
        )

        # Create players and teams
        player_positions = {
            str(player["player"]["id"]): Position(
                position_id=str(player["position"]["id"]),
                name=player["position"]["name"],
            )
            for raw_event in starting_xi_events
            for player in raw_event["tactics"]["lineup"]
        }

        starting_formations = {
            raw_event["team"]["id"]: FormationType(
                "-".join(list(str(raw_event["tactics"]["formation"])))
            )
            for raw_event in starting_xi_events
        }

        def create_team(lineup, ground_type):
            team = Team(
                team_id=str(lineup["team_id"]),
                name=lineup["team_name"],
                ground=ground_type,
                starting_formation=starting_formations[lineup["team_id"]],
            )
            team.players = [
                Player(
                    player_id=str(player["player_id"]),
                    team=team,
                    name=player["player_name"],
                    jersey_no=int(player["jersey_number"]),
                    starting=str(player["player_id"]) in player_positions,
                    position=player_positions.get(str(player["player_id"])),
                )
                for player in lineup["lineup"]
            ]
            return team

        home_team = create_team(home_lineup, Ground.HOME)
        away_team = create_team(away_lineup, Ground.AWAY)
        return [home_team, away_team]

    def create_periods(self, raw_events):
        half_start_and_end_events = [
            event.raw_event
            for event in raw_events.values()
            if SB.EVENT_TYPE(event.raw_event["type"])
            in [
                SB.EVENT_TYPE.HALF_START,
                SB.EVENT_TYPE.HALF_END,
            ]
        ][
            ::2
        ]  # recorded for each team, take every other
        periods = []
        for start_event, end_event in zip_longest(
            half_start_and_end_events[::2], half_start_and_end_events[1::2]
        ):
            if (
                start_event is None
                or SB.EVENT_TYPE(start_event["type"])
                != SB.EVENT_TYPE.HALF_START
                or SB.EVENT_TYPE(end_event["type"]) != SB.EVENT_TYPE.HALF_END
            ):
                raise DeserializationError(
                    "Failed to determine start and end time of periods."
                )
            start_timestamp = (
                periods[-1].end_timestamp
                + parse_str_ts(start_event["timestamp"])
                if len(periods) > 0
                else parse_str_ts(start_event["timestamp"])
            )
            end_timestamp = (
                start_timestamp + parse_str_ts(end_event["timestamp"])
                if end_event
                else None
            )
            period = Period(
                id=int(start_event["period"]),
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
            periods.append(period)
        return periods
