import collections
import json
import warnings
from collections import OrderedDict
from dataclasses import replace
from typing import Dict, List, NamedTuple, IO, Tuple
from datetime import timedelta, datetime
import logging

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
    SubstitutionEvent,
    Event,
    PassQualifier,
    PassType,
    PassEvent,
    ShotEvent,
    PitchDimensions,
    CoordinateSystem,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.infra.serializers.event.korastats.specification import (
    create_korastats_events,
    event_decoder,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

position_types_mapping: Dict[str, PositionType] = {
    "GK": PositionType.Goalkeeper,
    "SW": PositionType.CenterBack,
    "LB": PositionType.LeftBack,
    "LCB": PositionType.LeftCenterBack,
    "CB": PositionType.CenterBack,
    "RCB": PositionType.RightCenterBack,
    "RB": PositionType.RightBack,
    "LDM": PositionType.LeftDefensiveMidfield,
    "DM": PositionType.CenterDefensiveMidfield,
    "RDM": PositionType.RightDefensiveMidfield,
    "LCM": PositionType.LeftCentralMidfield,
    "CM": PositionType.CenterMidfield,
    "RCM": PositionType.RightCentralMidfield,
    "LAM": PositionType.LeftAttackingMidfield,
    "AM": PositionType.CenterAttackingMidfield,
    "RAM": PositionType.RightAttackingMidfield,
    "LW": PositionType.LeftWing,
    "SS": PositionType.Striker,
    "RW": PositionType.RightWing,
    "LCF": PositionType.LeftForward,
    "CF": PositionType.Striker,
    "RCF": PositionType.RightForward,
}


class KoraStatsInputs(NamedTuple):
    event_data: IO[bytes]
    meta_data: IO[bytes]


class KoraStatsDeserializer(EventDataDeserializer[KoraStatsInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.KORASTATS

    def deserialize(self, inputs: KoraStatsInputs) -> EventDataset:
        # Initialize coordinate system transformer
        self.transformer = self.get_transformer()

        with performance_logging("load data", logger=logger):
            metadata = json.load(inputs.meta_data)
            event_data = json.load(inputs.event_data)

        raw_events = event_data["events"]

        with performance_logging("parse data", logger=logger):
            teams = self.create_teams_and_players(metadata)

        # Create periods
        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_events)

        # Create events
        with performance_logging("parse events", logger=logger):
            events = []
            for ix, raw_event in enumerate(raw_events):
                prior_event = raw_events[ix - 1] if ix > 0 else None
                next_event = (
                    raw_events[ix + 1] if ix < len(raw_events) - 1 else None
                )
                korastats_event = event_decoder(raw_event)
                if korastats_event:
                    kloppy_events = korastats_event.set_refs(
                        periods, teams
                    ).deserialize(
                        self.event_factory, teams, prior_event, next_event
                    )
                    for event in kloppy_events:
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
            provider=Provider.KORASTATS,
            coordinate_system=self.transformer.get_to_coordinate_system(),
        )
        dataset = EventDataset(metadata=metadata, records=events)

        return dataset

    @staticmethod
    def create_teams_and_players(metadata: Dict) -> List[Team]:
        def create_team(team_info: Dict, ground: Ground) -> Team:
            starting_formation = FormationType.UNKNOWN

            team = Team(
                team_id=str(team_info["team"]["id"]),
                name=team_info["team"]["name"],
                ground=ground,
                starting_formation=starting_formation,
            )

            players = []
            for player_info in team_info["squad"]:
                starting_position = position_types_mapping[
                    player_info["position"]["name"]
                ]
                players.append(
                    Player(
                        player_id=str(player_info["id"]),
                        team=team,
                        name=player_info["name"],
                        jersey_no=player_info["shirt_number"],
                        starting_position=starting_position
                        if player_info["lineup"]
                        else None,
                        starting=True if player_info["lineup"] else False,
                    )
                )

            team.players = players

            return team

        home_team = create_team(metadata["home"], Ground.HOME)
        away_team = create_team(metadata["away"], Ground.AWAY)

        return [home_team, away_team]

    @staticmethod
    def create_periods(raw_events: List[Dict]) -> List[Period]:
        periods = []

        for idx, raw_event in enumerate(raw_events):
            next_period_id = None
            if (idx + 1) < len(raw_events):
                next_event = raw_events[idx + 1]
                next_period_id = next_event["half"]

            timestamp = timedelta(seconds=raw_event["timeInSec"])
            period_id = raw_event["half"]

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
                if len(periods) == 1:
                    periods[-1] = replace(
                        periods[-1],
                        end_timestamp=timestamp,
                    )
                else:
                    periods[-1] = replace(
                        periods[-1],
                        end_timestamp=periods[-2].end_timestamp + timestamp,
                    )

        return periods
