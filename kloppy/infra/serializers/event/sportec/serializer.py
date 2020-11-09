from collections import OrderedDict
from typing import Tuple, Dict, List
import logging
from datetime import datetime
from dateutil.parser import parse
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
    Position, Event, SetPieceQualifier, SetPieceType, Qualifier, BallOutEvent, RecoveryEvent, SubstitutionEvent,
    CardEvent, CardType,
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


def _event_chain_from_xml_elm(event_elm):
    chain = OrderedDict()
    current_elm = event_elm
    while True:
        chain[current_elm.tag] = dict(current_elm.attrib)
        if not current_elm.countchildren():
            break
        current_elm = current_elm.getchildren()[0]
    return chain


"""
{
    -'ChanceWithoutShot',
    'Offside',

    'BallClaiming',

     'TacklingGame',

    'Caution',
     'Foul',


    'ShotWide',
    'SuccessfulShot',
    'BlockedShot',
    'SavedShot',
    'OtherShot',

    'Cross',
     'Pass'

    'Substitution',


    'GoalDisallowed',
    'SpectacularPlay',
    'CautionTeamofficial',
    'OtherBallAction',
    'OtherPlayerAction',
     'Nutmeg',
     'FairPlay',
     'FinalWhistle',
     }


"""


SPORTEC_EVENT_NAME_KICKOFF = "KickOff"
SPORTEC_EVENT_NAME_FINAL_WHISTLE = "FinalWhistle"

SPORTEC_EVENT_NAME_SHOT_WIDE = "ShotWide"
SPORTEC_EVENT_NAME_SHOT_SAVED = "SavedShot"
SPORTEC_EVENT_NAME_SHOT_BLOCKED = "BlockedShot"
SPORTEC_EVENT_NAME_SHOT_WOODWORK = "ShotWoodWork"
SPORTEC_EVENT_NAME_SHOT_OTHER = "OtherShot"
SPORTEC_EVENT_NAME_SHOT_GOAL = "SuccessfulShot"
SPORTEC_SHOT_EVENT_NAMES = (
    SPORTEC_EVENT_NAME_SHOT_WIDE,
    SPORTEC_EVENT_NAME_SHOT_SAVED,
    SPORTEC_EVENT_NAME_SHOT_BLOCKED,
    SPORTEC_EVENT_NAME_SHOT_WOODWORK,
    SPORTEC_EVENT_NAME_SHOT_OTHER,
    SPORTEC_EVENT_NAME_SHOT_GOAL
)

SPORTEC_EVENT_NAME_PASS = "Pass"
SPORTEC_EVENT_NAME_CROSS = "Cross"
SPORTEC_EVENT_NAME_THROW_IN = "ThrowIn"
SPORTEC_EVENT_NAME_GOAL_KICK = "GoalKick"
SPORTEC_EVENT_NAME_PENALTY = "Penalty"
SPORTEC_EVENT_NAME_CORNER_KICK = "CornerKick"
SPORTEC_PASS_EVENT_NAMES = (
    SPORTEC_EVENT_NAME_PASS,
    SPORTEC_EVENT_NAME_CROSS
)

SPORTEC_EVENT_NAME_BALL_CLAIMING = "BallClaiming"
SPORTEC_EVENT_NAME_SUBSTITUTION = "Substitution"
SPORTEC_EVENT_NAME_CAUTION = "Caution"


def _parse_datetime(dt_str: str) -> float:
    return parse(dt_str).timestamp()


def _get_event_qualifiers(event_chain: Dict) -> List[Qualifier]:
    qualifiers = []
    if SPORTEC_EVENT_NAME_THROW_IN in event_chain:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.THROW_IN))
    elif SPORTEC_EVENT_NAME_GOAL_KICK in event_chain:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.GOAL_KICK))
    elif SPORTEC_EVENT_NAME_PENALTY in event_chain:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.PENALTY))
    elif SPORTEC_EVENT_NAME_CORNER_KICK in event_chain:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.CORNER_KICK))
    elif SPORTEC_EVENT_NAME_KICKOFF in event_chain:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.KICK_OFF))
    return qualifiers


def _parse_shot(event_name: str, event_chain: OrderedDict) -> Dict:
    if event_name == SPORTEC_EVENT_NAME_SHOT_WIDE:
        result = ShotResult.OFF_TARGET
    elif event_name == SPORTEC_EVENT_NAME_SHOT_SAVED:
        result = ShotResult.SAVED
    elif event_name == SPORTEC_EVENT_NAME_SHOT_BLOCKED:
        result = ShotResult.BLOCKED
    elif event_name == SPORTEC_EVENT_NAME_SHOT_WOODWORK:
        result = ShotResult.POST
    elif event_name == SPORTEC_EVENT_NAME_SHOT_GOAL:
        result = ShotResult.GOAL
    elif event_name == SPORTEC_EVENT_NAME_SHOT_OTHER:
        result = None
    else:
        raise ValueError(f"Unknown shot type {event_name}")

    return dict(result=result, qualifiers=_get_event_qualifiers(event_chain))


def _parse_pass(event_chain: OrderedDict) -> Dict:
    if event_chain['Play']['Evaluation'] in ('successfullyCompleted', 'successful'):
        result = PassResult.COMPLETE
    else:
        result = PassResult.INCOMPLETE

    return dict(result=result, qualifiers=_get_event_qualifiers(event_chain))


def _parse_substitution(event_attributes: Dict, team: Team) -> Dict:
    return dict(
        player=team.get_player_by_id(event_attributes['PlayerOut']),
        replacement_player=team.get_player_by_id(event_attributes['PlayerIn'])
    )


def _parse_caution(event_attributes: Dict) -> Dict:
    if event_attributes['CardColor'] == 'yellow':
        card_type = CardType.FIRST_YELLOW
    elif event_attributes['CardColor'] == 'yellowRed':
        card_type = CardType.SECOND_YELLOW
    elif event_attributes['CardColor'] == 'red':
        card_type = CardType.RED
    else:
        raise ValueError(f"Unknown card color: {event_attributes['CardColor']}")

    return dict(
        card_type=card_type
    )


def _include_event(event: Event, wanted_event_types: List) -> bool:
    return not wanted_event_types or event.event_type in wanted_event_types


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

            periods = []
            period_id = 0
            events = []

            for event_elm in event_root.iterchildren('Event'):
                event_chain = _event_chain_from_xml_elm(event_elm)
                timestamp = _parse_datetime(event_chain['Event']['EventTime'])
                if SPORTEC_EVENT_NAME_KICKOFF in event_chain and 'GameSection' in event_chain[SPORTEC_EVENT_NAME_KICKOFF]:
                    period_id += 1
                    period = Period(
                        id=period_id,
                        start_timestamp=timestamp,
                        end_timestamp=None
                    )
                    periods.append(period)
                elif SPORTEC_EVENT_NAME_FINAL_WHISTLE in event_chain:
                    period.end_timestamp = timestamp
                    continue

                generic_event_kwargs = dict(
                    # from DataRecord
                    period=period,
                    timestamp=timestamp - period.start_timestamp,
                    ball_owning_team=None,
                    ball_state=BallState.ALIVE,
                    # from Event
                    event_id=event_chain['Event']['EventId'],
                    coordinates=None,
                    raw_event=event_elm,
                    team=None,
                    player=None
                )

                team = None
                for event_attributes in event_chain.values():
                    if 'Team' in event_attributes:
                        team = home_team if event_attributes['Team'] == home_team.team_id else away_team
                        generic_event_kwargs['team'] = team
                    if 'Player' in event_attributes:
                        if not team:
                            raise ValueError("Player set while team is not set")
                        player = team.get_player_by_id(event_attributes['Player'])
                        generic_event_kwargs['player'] = player

                event_name, event_attributes = event_chain.popitem()
                if event_name in SPORTEC_SHOT_EVENT_NAMES:
                    shot_event_kwargs = _parse_shot(
                        event_name=event_name,
                        event_chain=event_chain
                    )
                    event = ShotEvent.create(
                        **shot_event_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_name in SPORTEC_PASS_EVENT_NAMES:
                    pass_event_kwargs = _parse_pass(
                        event_chain=event_chain
                    )
                    event = PassEvent.create(
                        **pass_event_kwargs,
                        **generic_event_kwargs,
                        receive_timestamp=None,
                        receiver_player=None,
                        receiver_coordinates=None
                    )
                elif event_name == SPORTEC_EVENT_NAME_BALL_CLAIMING:
                    event = RecoveryEvent.create(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )
                elif event_name == SPORTEC_EVENT_NAME_SUBSTITUTION:
                    substitution_event_kwargs = _parse_substitution(
                        event_attributes=event_attributes, team=team
                    )
                    generic_event_kwargs['player'] = substitution_event_kwargs['player']
                    del substitution_event_kwargs['player']
                    event = SubstitutionEvent.create(
                        result=None,
                        qualifiers=None,
                        **substitution_event_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_name == SPORTEC_EVENT_NAME_CAUTION:
                    card_kwargs = _parse_caution(event_attributes)
                    event = CardEvent.create(
                        result=None,
                        qualifiers=None,
                        **card_kwargs,
                        **generic_event_kwargs,
                    )
                else:
                    event = GenericEvent.create(
                        result=None,
                        qualifiers=None,
                        event_name=event_name,
                        **generic_event_kwargs,
                    )

                if event.event_type == EventType.PASS and \
                    event.get_qualifier_value(SetPieceQualifier) in (SetPieceType.THROW_IN, SetPieceType.GOAL_KICK):
                    # 1. update previous pass
                    if events[-1].event_type == EventType.PASS:
                        events[-1].result = PassResult.OUT

                    # 2. add synthetic out event
                    decision_timestamp = _parse_datetime(
                        event_chain[list(event_chain.keys())[1]]['DecisionTimestamp']
                    )
                    out_event = BallOutEvent.create(
                        period=period,
                        timestamp=decision_timestamp - period.start_timestamp,
                        ball_owning_team=None,
                        ball_state=BallState.DEAD,
                        # from Event
                        event_id=event_chain['Event']['EventId'],
                        team=events[-1].team,
                        player=events[-1].player,
                        coordinates=None,
                        raw_event=None,
                        result=None,
                        qualifiers=None
                    )
                    events.append(out_event)

                events.append(event)

        events = list(
            filter(lambda _event: _include_event(_event, wanted_event_types), events)
        )

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
