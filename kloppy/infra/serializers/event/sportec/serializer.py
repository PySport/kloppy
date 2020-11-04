from typing import Tuple, Dict, List
import logging
from datetime import datetime
import pytz
from lxml import objectify

from kloppy.domain import (
    EventDataset,
    Team,
    Period,
    Point,
    BallState,
    DatasetFlag,
    Orientation,
    PitchDimensions,
    Dimension,
    PassEvent,
    ShotEvent,
    TakeOnEvent,
    CarryEvent,
    GenericEvent,
    PassResult,
    ShotResult,
    TakeOnResult,
    CarryResult,
    EventType,
    Ground,
    Score,
    Provider,
    Metadata,
    Player,
    Position,
)
from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.utils import Readable, performance_logging

logger = logging.getLogger(__name__)


def _team_from_xml_elm(team_elm) -> Team:
    team = Team(
        team_id=team_elm.attrib["TeamId"],
        name=team_elm.attrib['TeamName'],
        ground=Ground.HOME
        if team_elm.attrib["Role"] == "home"
        else Ground.AWAY,
    )
    team.players = [
        Player(
            player_id=player_elm.attrib["PersonId"],
            team=team,
            jersey_no=int(player_elm.attrib["ShirtNumber"]),
            name=player_elm.attrib['Shortname'],
            first_name=player_elm.attrib['FirstName'],
            last_name=player_elm.attrib['LastName'],
            position=Position(
                position_id=None,
                name=player_elm.attrib["PlayingPosition"],
                coordinates=None,
            ) if 'PlayingPosition' in player_elm.attrib else None,
            starting=player_elm.attrib['Starting'] == 'true'
        )
        for player_elm in team_elm.Players.iterchildren("Player")
    ]
    return team


class SportecEventSerializer(EventDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "match_data" not in inputs:
            raise ValueError("Please specify a value for input 'match_data'")
        if "event_data" not in inputs:
            raise ValueError("Please specify a value for input 'event_data'")

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> EventDataset:
        self.__validate_inputs(inputs)
        if not options:
            options = {}

        with performance_logging("load data", logger=logger):
            match_root = objectify.fromstring(inputs["match_data"].read())
            event_root = objectify.fromstring(inputs["event_data"].read())

            wanted_event_types = [
                EventType[event_type.upper()]
                for event_type in options.get("event_types", [])
            ]

        with performance_logging("parse data", logger=logger):
            x_max = float(match_root.MatchInformation.Environment.attrib['PitchX'])
            y_max = float(match_root.MatchInformation.Environment.attrib['PitchY'])

            team_path = objectify.ObjectPath(
                "PutDataRequest.MatchInformation.Teams"
            )
            team_elms = list(
                team_path.find(match_root).iterchildren("Team")
            )

            for team_elm in team_elms:
                if team_elm.attrib["Role"] == "home":
                    home_team = _team_from_xml_elm(team_elm)
                elif team_elm.attrib["Role"] == "guest":
                    away_team = _team_from_xml_elm(team_elm)
                else:
                    raise Exception(f"Unknown side: {team_elm.attrib['Role']}")

            home_score, away_score = match_root.MatchInformation.General.attrib['Result'].split(':')
            score = Score(home=int(home_score), away=int(away_score))
            teams = [home_team, away_team]

            if len(home_team.players) == 0 or len(away_team.players) == 0:
                raise Exception("LineUp incomplete")

            periods = [
                Period(
                    id=1,
                    start_timestamp=None,
                    end_timestamp=None,
                ),
                Period(
                    id=2,
                    start_timestamp=None,
                    end_timestamp=None,
                ),
            ]
            events = []

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=PitchDimensions(
                x_dim=Dimension(0, x_max), y_dim=Dimension(0, y_max)
            ),
            score=score,
            frame_rate=None,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM,
            provider=Provider.SPORTEC,
        )

        return EventDataset(
            metadata=metadata,
            records=events,
        )

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
