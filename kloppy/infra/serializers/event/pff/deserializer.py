from datetime import timedelta
import json
import logging
from itertools import zip_longest
from typing import IO, NamedTuple

from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    FormationType,
    Ground,
    Metadata,
    Orientation,
    Period,
    Player,
    Provider,
    Team,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging

from . import specification as PFF

logger = logging.getLogger(__name__)


class PFFEventInputs(NamedTuple):
    metadata: IO[bytes]
    players: IO[bytes]
    raw_event_data: IO[bytes]


class PFFEventDeserializer(EventDataDeserializer[PFFEventInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.PFF

    def deserialize(
        self, inputs: PFFEventInputs, additional_metadata: dict
    ) -> EventDataset:
        # Intialize coordinate system transformer
        self.transformer = self.get_transformer()

        # Load data from JSON files
        # and determine fidelity versions for x/y coordinates
        with performance_logging("load data", logger=logger):
            metadata = json.load(inputs.metadata)
            players = json.load(inputs.players)
            raw_events = json.load(inputs.raw_event_data)

        # Create teams and players
        with performance_logging("parse teams ans players", logger=logger):
            teams = self.create_teams_and_players(metadata, players)

        # Create periods
        with performance_logging("parse periods", logger=logger):
            periods = self.create_periods(raw_events)

        # Create events
        # with performance_logging("parse events", logger=logger):
        #     events = []
        #     for raw_event in raw_event_data:
        #         new_events = (
        #             raw_event
        #                 .set_refs(periods, teams, raw_events)
        #                 .deserialize(self.event_factory)
        #         )
        #         for event in new_events:
        #             if self.should_include_event(event):
        #                 # Transform event to the coordinate system
        #                 event = self.transformer.transform_event(event)
        #                 events.append(event)

        events = []

        pff_metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=self.transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=None,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            score=None,
            provider=Provider.PFF,
            coordinate_system=self.transformer.get_to_coordinate_system(),
            **additional_metadata,
        )
        dataset = EventDataset(metadata=pff_metadata, records=events)

#         for event in dataset:
#             if "homePlayers" in event.raw_event:
#                 # TODO: Freeze frame parsing
#                 # event.freeze_frame = self.transformer.transform_frame(
#                     # parse_freeze_frame(
#                     #     freeze_frame=event.raw_event["shot"]["freeze_frame"],
#                     #     home_team=teams[0],
#                     #     away_team=teams[1],
#                     #     event=event,
#                     #     fidelity_version=data_version.shot_fidelity_version,
#                     # )
#                 # )
        return dataset

    def create_teams_and_players(self, metadata, players):
        print(players)
        print(metadata)
        def create_team(team_id, team_name, ground_type):
            team = Team(
                team_id=team_id,
                name=team_name,
                ground=ground_type,
            )
            team.players = [
                Player(
                    player_id=entry["player"]["id"],
                    team=team,
                    name=entry['player']["nickname"],
                    jersey_no=int(entry["shirtNumber"]),
                    starting_position=PFF.position_types_mapping[entry['positionGroupType']]
                )
                for entry in players
                if entry['team']['id'] == team_id
            ]
            return team

        home_team = metadata["homeTeam"]
        away_team = metadata["awayTeam"]

        home = create_team(home_team['id'], home_team['name'], Ground.HOME)
        away = create_team(away_team['id'], away_team['name'], Ground.AWAY)
        return [home, away]

    def create_periods(self, raw_event_data: list[dict]) -> list[Period]:
        half_start_events = {}
        half_end_events = {}

        for event in raw_event_data:
            event_type = PFF.EVENT_TYPE(event["gameEvents"]["gameEventType"])
            period = event["gameEvents"]["period"] 

            if event_type in [
                PFF.EVENT_TYPE.FIRST_HALF_KICKOFF,
                PFF.EVENT_TYPE.SECOND_HALF_KICKOFF,
                PFF.EVENT_TYPE.THIRD_HALF_KICKOFF,
                PFF.EVENT_TYPE.FOURTH_HALF_KICKOFF,
            ]:
                half_start_events[period] = event
            elif event_type == PFF.EVENT_TYPE.END_OF_HALF:
                half_end_events[period] = event

        periods = []

        for start_event, end_event in zip_longest(
            half_start_events.values(), half_end_events.values()
        ):
            if start_event is None or end_event is None:
                raise DeserializationError(
                    "Failed to determine start and end time of periods."
                )

            period = Period(
                id=int(start_event["gameEvents"]["period"]),
                start_timestamp=timedelta(seconds=start_event["startTime"]),
                end_timestamp=timedelta(seconds=end_event['startTime']),
            )
            periods.append(period)

        return periods
