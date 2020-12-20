from typing import Tuple, Dict, List
import logging
import json

from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.utils import Readable, performance_logging

from kloppy.domain import (
    EventDataset,
    Metadata,
    Provider,
    Team,
    Ground,
    Player,
    Position,
    ShotEvent,
    ShotResult,
    Point,
)

logger = logging.getLogger(__name__)


def _parse_team(raw_events: List[Dict], wyId: str, ground: Ground) -> Team:
    team = Team(
        team_id=wyId,
        name=raw_events["teams"][wyId]["officialName"],
        ground=ground,
    )
    team.players = [
        Player(
            player_id=str(p["playerId"]),
            team=team,
            jersey_no=None,
            first_name=p["player"]["firstName"],
            last_name=p["player"]["lastName"],
        )
        for p in raw_events["players"][wyId]
    ]
    return team


def _parse_shot(raw_event: Dict) -> Dict:
    tags = [t["id"] for t in raw_event["tags"]]

    result = None
    if 101 in tags:
        result = ShotResult.GOAL

    return {
        "result": result,
        "qualifiers": None,
    }


class WyscoutSerializer(EventDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        pass

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> EventDataset:
        WyscoutSerializer.__validate_inputs(inputs)

        if not options:
            options = {}

        with performance_logging("parse data", logger=logger):
            raw_events = json.load(inputs["event_data"])

        with performance_logging("parse data", logger=logger):
            home_team_id, away_team_id = raw_events["teams"].keys()
            home_team = _parse_team(raw_events, home_team_id, Ground.HOME)
            away_team = _parse_team(raw_events, away_team_id, Ground.AWAY)
            teams = [home_team, away_team]

            events = []
            for raw_event in raw_events["events"]:
                generic_event_args = {
                    "event_id": raw_event["id"],
                    "raw_event": raw_event,
                    "coordinates": Point(**raw_event["positions"][0]),
                    "team": None,
                    "player": None,
                    "ball_owning_team": None,
                    "ball_state": None,
                    "period": None,
                    "timestamp": raw_event["eventSec"],
                }

                event = None
                if raw_event["eventName"] == 10:
                    shot_event_args = _parse_shot(raw_event)
                    event = ShotEvent.create(
                        **shot_event_args, **generic_event_args
                    )

                if event:
                    print(event)
                    events.append(event)

        metadata = Metadata(
            teams=teams,
            periods=[],
            pitch_dimensions=None,
            score=None,
            frame_rate=None,
            orientation=None,
            flags=None,
            provider=Provider.WYSCOUT,
        )

        return EventDataset(metadata=metadata, records=events)

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
