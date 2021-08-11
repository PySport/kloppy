from collections import OrderedDict
from typing import Tuple, Dict, List
import logging
from dateutil.parser import parse
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
    GenericEvent,
    PassResult,
    ShotResult,
    EventType,
    Ground,
    Score,
    Provider,
    Metadata,
    Player,
    Position,
    Event,
    SetPieceQualifier,
    SetPieceType,
    BodyPartQualifier,
    BodyPart,
    Qualifier,
    BallOutEvent,
    RecoveryEvent,
    SubstitutionEvent,
    CardEvent,
    CardType,
    FoulCommittedEvent,
    AttackingDirection,
    build_coordinate_system,
    Transformer,
)
from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.utils import Readable, performance_logging

logger = logging.getLogger(__name__)


def _team_from_xml_elm(team_elm) -> Team:
    team = Team(
        team_id=team_elm.attrib["TeamId"],
        name=team_elm.attrib["TeamName"],
        ground=Ground.HOME
        if team_elm.attrib["Role"] == "home"
        else Ground.AWAY,
    )
    team.players = [
        Player(
            player_id=player_elm.attrib["PersonId"],
            team=team,
            jersey_no=int(player_elm.attrib["ShirtNumber"]),
            name=player_elm.attrib["Shortname"],
            first_name=player_elm.attrib["FirstName"],
            last_name=player_elm.attrib["LastName"],
            position=Position(
                position_id=None,
                name=player_elm.attrib["PlayingPosition"],
                coordinates=None,
            )
            if "PlayingPosition" in player_elm.attrib
            else None,
            starting=player_elm.attrib["Starting"] == "true",
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
    SPORTEC_EVENT_NAME_SHOT_GOAL,
)

SPORTEC_EVENT_NAME_PASS = "Pass"
SPORTEC_EVENT_NAME_CROSS = "Cross"
SPORTEC_EVENT_NAME_THROW_IN = "ThrowIn"
SPORTEC_EVENT_NAME_GOAL_KICK = "GoalKick"
SPORTEC_EVENT_NAME_PENALTY = "Penalty"
SPORTEC_EVENT_NAME_CORNER_KICK = "CornerKick"
SPORTEC_EVENT_NAME_FREE_KICK = "FreeKick"
SPORTEC_PASS_EVENT_NAMES = (SPORTEC_EVENT_NAME_PASS, SPORTEC_EVENT_NAME_CROSS)

SPORTEC_EVENT_NAME_BALL_CLAIMING = "BallClaiming"
SPORTEC_EVENT_NAME_SUBSTITUTION = "Substitution"
SPORTEC_EVENT_NAME_CAUTION = "Caution"
SPORTEC_EVENT_NAME_FOUL = "Foul"

SPORTEC_EVENT_TYPE_OF_SHOT = "TypeOfShot"
SPORTEC_EVENT_BODY_PART_HEAD = "head"
SPORTEC_EVENT_BODY_PART_LEFT_FOOT = "leftLeg"
SPORTEC_EVENT_BODY_PART_RIGHT_FOOT = "rightLeg"


def _parse_datetime(dt_str: str) -> float:
    return parse(dt_str).timestamp()


def _get_event_qualifiers(event_chain: Dict) -> List[Qualifier]:
    qualifiers = []

    qualifiers.extend(_get_event_setpiece_qualifiers(event_chain))
    qualifiers.extend(_get_event_bodypart_qualifiers(event_chain))

    return qualifiers


def _get_event_setpiece_qualifiers(event_chain):
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
    elif SPORTEC_EVENT_NAME_FREE_KICK in event_chain:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))

    return qualifiers


def _get_event_bodypart_qualifiers(event_chain):
    qualifiers = []

    if SPORTEC_EVENT_BODY_PART_HEAD in [
        item.get(SPORTEC_EVENT_TYPE_OF_SHOT) for item in event_chain.values()
    ]:
        qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))
    elif SPORTEC_EVENT_BODY_PART_LEFT_FOOT in [
        item.get(SPORTEC_EVENT_TYPE_OF_SHOT) for item in event_chain.values()
    ]:
        qualifiers.append(BodyPartQualifier(value=BodyPart.LEFT_FOOT))
    elif SPORTEC_EVENT_BODY_PART_RIGHT_FOOT in [
        item.get(SPORTEC_EVENT_TYPE_OF_SHOT) for item in event_chain.values()
    ]:
        qualifiers.append(BodyPartQualifier(value=BodyPart.RIGHT_FOOT))

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


def _parse_pass(event_chain: OrderedDict, team: Team) -> Dict:
    if event_chain["Play"]["Evaluation"] in (
        "successfullyCompleted",
        "successful",
    ):
        result = PassResult.COMPLETE
        if "Recipient" in event_chain["Play"]:
            receiver_player = team.get_player_by_id(
                event_chain["Play"]["Recipient"]
            )
        else:
            # this attribute can be missing according to docs
            receiver_player = None
    else:
        result = PassResult.INCOMPLETE
        receiver_player = None

    return dict(
        result=result,
        receiver_player=receiver_player,
        qualifiers=_get_event_qualifiers(event_chain),
    )


def _parse_substitution(event_attributes: Dict, team: Team) -> Dict:
    return dict(
        player=team.get_player_by_id(event_attributes["PlayerOut"]),
        replacement_player=team.get_player_by_id(event_attributes["PlayerIn"]),
    )


def _parse_caution(event_attributes: Dict) -> Dict:
    if event_attributes["CardColor"] == "yellow":
        card_type = CardType.FIRST_YELLOW
    elif event_attributes["CardColor"] == "yellowRed":
        card_type = CardType.SECOND_YELLOW
    elif event_attributes["CardColor"] == "red":
        card_type = CardType.RED
    else:
        raise ValueError(
            f"Unknown card color: {event_attributes['CardColor']}"
        )

    return dict(card_type=card_type)


def _parse_foul(event_attributes: Dict, teams: List[Team]) -> Dict:
    team = (
        teams[0]
        if event_attributes["TeamFouler"] == teams[0].team_id
        else teams[1]
    )
    player = team.get_player_by_id(event_attributes["Fouler"])

    return dict(team=team, player=player)


def _parse_coordinates(event_attributes: Dict) -> Point:
    if "X-Position" not in event_attributes:
        return None
    return Point(
        x=float(event_attributes["X-Position"]),
        y=float(event_attributes["Y-Position"]),
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
            x_max = float(
                match_root.MatchInformation.Environment.attrib["PitchX"]
            )
            y_max = float(
                match_root.MatchInformation.Environment.attrib["PitchY"]
            )

            from_coordinate_system = build_coordinate_system(
                Provider.SPORTEC,
                length=x_max,
                width=y_max,
            )

            to_coordinate_system = build_coordinate_system(
                options.get("coordinate_system", Provider.KLOPPY),
                length=x_max,
                width=y_max,
            )

            transformer = Transformer(
                from_coordinate_system=from_coordinate_system,
                to_coordinate_system=to_coordinate_system,
            )

            team_path = objectify.ObjectPath(
                "PutDataRequest.MatchInformation.Teams"
            )
            team_elms = list(team_path.find(match_root).iterchildren("Team"))

            for team_elm in team_elms:
                if team_elm.attrib["Role"] == "home":
                    home_team = _team_from_xml_elm(team_elm)
                elif team_elm.attrib["Role"] == "guest":
                    away_team = _team_from_xml_elm(team_elm)
                else:
                    raise Exception(f"Unknown side: {team_elm.attrib['Role']}")

            (
                home_score,
                away_score,
            ) = match_root.MatchInformation.General.attrib["Result"].split(":")
            score = Score(home=int(home_score), away=int(away_score))
            teams = [home_team, away_team]

            if len(home_team.players) == 0 or len(away_team.players) == 0:
                raise Exception("LineUp incomplete")

            periods = []
            period_id = 0
            events = []

            for event_elm in event_root.iterchildren("Event"):
                event_chain = _event_chain_from_xml_elm(event_elm)
                timestamp = _parse_datetime(event_chain["Event"]["EventTime"])
                if (
                    SPORTEC_EVENT_NAME_KICKOFF in event_chain
                    and "GameSection"
                    in event_chain[SPORTEC_EVENT_NAME_KICKOFF]
                ):
                    period_id += 1
                    period = Period(
                        id=period_id,
                        start_timestamp=timestamp,
                        end_timestamp=None,
                    )
                    if period_id == 1:
                        team_left = event_chain[SPORTEC_EVENT_NAME_KICKOFF][
                            "TeamLeft"
                        ]
                        if team_left == home_team.team_id:
                            # goal of home team is on the left side.
                            # this means they attack from left to right
                            orientation = Orientation.FIXED_HOME_AWAY
                            period.set_attacking_direction(
                                AttackingDirection.HOME_AWAY
                            )
                        else:
                            orientation = Orientation.FIXED_AWAY_HOME
                            period.set_attacking_direction(
                                AttackingDirection.AWAY_HOME
                            )
                    else:
                        last_period = periods[-1]
                        period.set_attacking_direction(
                            AttackingDirection.AWAY_HOME
                            if last_period.attacking_direction
                            == AttackingDirection.HOME_AWAY
                            else AttackingDirection.HOME_AWAY
                        )

                    periods.append(period)
                elif SPORTEC_EVENT_NAME_FINAL_WHISTLE in event_chain:
                    period.end_timestamp = timestamp
                    continue

                team = None
                player = None
                flatten_attributes = dict()
                # reverse because top levels are more important
                for event_attributes in reversed(event_chain.values()):
                    flatten_attributes.update(event_attributes)

                if "Team" in flatten_attributes:
                    team = (
                        home_team
                        if flatten_attributes["Team"] == home_team.team_id
                        else away_team
                    )
                if "Player" in flatten_attributes:
                    if not team:
                        raise ValueError("Player set while team is not set")
                    player = team.get_player_by_id(
                        flatten_attributes["Player"]
                    )

                generic_event_kwargs = dict(
                    # from DataRecord
                    period=period,
                    timestamp=timestamp - period.start_timestamp,
                    ball_owning_team=None,
                    ball_state=BallState.ALIVE,
                    # from Event
                    event_id=event_chain["Event"]["EventId"],
                    coordinates=_parse_coordinates(event_chain["Event"]),
                    raw_event=flatten_attributes,
                    team=team,
                    player=player,
                )

                event_name, event_attributes = event_chain.popitem()
                if event_name in SPORTEC_SHOT_EVENT_NAMES:
                    shot_event_kwargs = _parse_shot(
                        event_name=event_name, event_chain=event_chain
                    )
                    event = ShotEvent.create(
                        **shot_event_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_name in SPORTEC_PASS_EVENT_NAMES:
                    pass_event_kwargs = _parse_pass(
                        event_chain=event_chain, team=team
                    )
                    event = PassEvent.create(
                        **pass_event_kwargs,
                        **generic_event_kwargs,
                        receive_timestamp=None,
                        receiver_coordinates=None,
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
                    generic_event_kwargs["player"] = substitution_event_kwargs[
                        "player"
                    ]
                    del substitution_event_kwargs["player"]
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
                elif event_name == SPORTEC_EVENT_NAME_FOUL:
                    foul_kwargs = _parse_foul(event_attributes, teams=teams)
                    generic_event_kwargs.update(foul_kwargs)
                    event = FoulCommittedEvent.create(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )
                else:
                    event = GenericEvent.create(
                        result=None,
                        qualifiers=None,
                        event_name=event_name,
                        **generic_event_kwargs,
                    )

                if events:
                    previous_event = events[-1]
                    if (
                        previous_event.event_type == EventType.PASS
                        and previous_event.result == PassResult.COMPLETE
                    ):
                        if "X-Source-Position" in event_chain["Event"]:
                            previous_event.receiver_coordinates = Point(
                                x=float(
                                    event_chain["Event"]["X-Source-Position"]
                                ),
                                y=float(
                                    event_chain["Event"]["Y-Source-Position"]
                                ),
                            )

                if (
                    event.event_type == EventType.PASS
                    and event.get_qualifier_value(SetPieceQualifier)
                    in (
                        SetPieceType.THROW_IN,
                        SetPieceType.GOAL_KICK,
                        SetPieceType.CORNER_KICK,
                    )
                ):
                    # 1. update previous pass
                    if events[-1].event_type == EventType.PASS:
                        events[-1].result = PassResult.OUT

                    # 2. add synthetic out event
                    decision_timestamp = _parse_datetime(
                        event_chain[list(event_chain.keys())[1]][
                            "DecisionTimestamp"
                        ]
                    )
                    out_event = BallOutEvent.create(
                        period=period,
                        timestamp=decision_timestamp - period.start_timestamp,
                        ball_owning_team=None,
                        ball_state=BallState.DEAD,
                        # from Event
                        event_id=event_chain["Event"]["EventId"] + "-ball-out",
                        team=events[-1].team,
                        player=events[-1].player,
                        coordinates=None,
                        raw_event={},
                        result=None,
                        qualifiers=None,
                    )
                    events.append(transformer.transform_event(out_event))

                events.append(transformer.transform_event(event))

        events = list(
            filter(
                lambda _event: _include_event(_event, wanted_event_types),
                events,
            )
        )

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=to_coordinate_system.pitch_dimensions,
            score=score,
            frame_rate=None,
            orientation=orientation,
            flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
            provider=Provider.SPORTEC,
            coordinate_system=to_coordinate_system,
        )

        return EventDataset(
            metadata=metadata,
            records=events,
        )

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
