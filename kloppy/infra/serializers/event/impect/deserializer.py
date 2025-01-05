import json
from collections import OrderedDict
from dataclasses import replace
from typing import Dict, List, NamedTuple, IO
from datetime import timedelta, datetime
import logging
from lxml import objectify

from kloppy.domain import (
    EventDataset,
    Team,
    Period,
    Point,
    BallState,
    DatasetFlag,
    Orientation,
    PassResult,
    ShotResult,
    EventType,
    Ground,
    Score,
    Provider,
    Metadata,
    Player,
    SetPieceQualifier,
    SetPieceType,
    BodyPartQualifier,
    BodyPart,
    Qualifier,
    CardType,
    PositionType,
    Official,
    OfficialType,
    FormationType,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.infra.serializers.event.impect.specification import (
    event_decoder,
    create_impect_events,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)


class ImpectInputs(NamedTuple):
    meta_data: IO[bytes]
    event_data: IO[bytes]


class ImpectDeserializer(EventDataDeserializer[ImpectInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.IMPECT

    def deserialize(self, inputs: ImpectInputs) -> EventDataset:
        # Intialize coordinate system transformer
        self.transformer = self.get_transformer()

        with performance_logging("load data", logger=logger):
            metadata = json.load(inputs.meta_data)
            raw_events = json.load(inputs.event_data)

        with performance_logging("parse data", logger=logger):
            teams = self.create_teams_and_players(metadata)

        # Create periods
        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_events)

        # Create events
        with performance_logging("parse events", logger=logger):
            events = []
            impect_events = create_impect_events(raw_events)
            for impect_event in impect_events.values():
                new_events = impect_event.set_refs(
                    periods, teams, impect_events
                ).deserialize(self.event_factory)
                for event in new_events:
                    if self.should_include_event(event):
                        # Transform event to the coordinate system
                        event = self.transformer.transform_event(event)
                        events.append(event)

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            provider=Provider.IMPECT,
            coordinate_system=self.transformer.get_to_coordinate_system(),
        )
        dataset = EventDataset(metadata=metadata, records=events)

        return dataset

    @staticmethod
    def create_teams_and_players(metadata: Dict) -> List[Team]:
        def create_team(team_info: Dict, ground: Ground) -> Team:
            def get_position(player_starting_info) -> PositionType:

                return PositionType.RightForward

            team = Team(
                team_id=str(team_info["id"]),
                name="",
                ground=ground,
                starting_formation=FormationType.FOUR_FOUR_TWO,
                # starting_formation=formation_mapping[team_info["startingFormation"]]
            )
            player_starting_positions = {
                player_starting_info["playerId"]: get_position(
                    player_starting_info
                )
                for player_starting_info in team_info["startingPositions"]
            }

            players = []
            for player in team_info["players"]:
                starting_position = player_starting_positions.get(player["id"])
                players.append(
                    Player(
                        player_id=str(player["id"]),
                        team=team,
                        name="",
                        jersey_no=player["shirtNumber"],
                        starting_position=starting_position,
                        starting=True if starting_position else False,
                    )
                )

            team.players = players

            return team

        home_team = create_team(metadata["squadHome"], Ground.HOME)
        away_team = create_team(metadata["squadAway"], Ground.AWAY)

        return [home_team, away_team]

    @staticmethod
    def create_periods(raw_events: List[Dict]) -> List[Period]:
        periods = []

        for idx, raw_event in enumerate(raw_events):
            next_period_id = None
            if (idx + 1) < len(raw_events):
                next_event = raw_events[idx + 1]
                next_period_id = next_event["periodId"]

            timestamp = raw_event["gameTime"]["gameTimeInSec"]
            period_id = raw_event["periodId"]

            if len(periods) == 0 or periods[-1].id != period_id:
                periods.append(
                    Period(
                        id=period_id,
                        start_timestamp=(
                            timedelta(seconds=0)
                            if len(periods) == 0
                            else periods[-1].end_timestamp
                        ),
                        end_timestamp=None,
                    )
                )

            if next_period_id != period_id:
                periods[-1] = replace(
                    periods[-1],
                    end_timestamp=timedelta(seconds=timestamp),
                )

        return periods
