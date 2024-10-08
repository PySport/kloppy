from collections import OrderedDict
from typing import Dict, List, NamedTuple, IO
from datetime import timedelta, datetime, timezone
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
    PassResult,
    ShotResult,
    EventType,
    Ground,
    Score,
    Provider,
    Metadata,
    Player,
    Position,
    SetPieceQualifier,
    SetPieceType,
    BodyPartQualifier,
    BodyPart,
    Qualifier,
    CardType,
    AttackingDirection,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging

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
            starting_position=Position(
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


SPORTEC_FPS = 25

"""Sportec uses fixed starting frame ids for each half"""
SPORTEC_FIRST_HALF_STARTING_FRAME_ID = 10_000
SPORTEC_SECOND_HALF_STARTING_FRAME_ID = 100_000
SPORTEC_FIRST_EXTRA_HALF_STARTING_FRAME_ID = 200_000
SPORTEC_SECOND_EXTRA_HALF_STARTING_FRAME_ID = 250_000


class SportecMetadata(NamedTuple):
    score: Score
    teams: List[Team]
    periods: List[Period]
    x_max: float
    y_max: float
    fps: int


def sportec_metadata_from_xml_elm(match_root) -> SportecMetadata:
    """
    Load metadata from Sportec XML element. This part is shared between event- and tracking data.
    In the future this might move to a common.sportec package that provides functionality for both
    deserializers.
    """
    x_max = float(match_root.MatchInformation.Environment.attrib["PitchX"])
    y_max = float(match_root.MatchInformation.Environment.attrib["PitchY"])

    team_path = objectify.ObjectPath("PutDataRequest.MatchInformation.Teams")
    team_elms = list(team_path.find(match_root).iterchildren("Team"))

    home_team = away_team = None
    for team_elm in team_elms:
        if team_elm.attrib["Role"] == "home":
            home_team = _team_from_xml_elm(team_elm)
        elif team_elm.attrib["Role"] == "guest":
            away_team = _team_from_xml_elm(team_elm)
        else:
            raise DeserializationError(
                f"Unknown side: {team_elm.attrib['Role']}"
            )

    if not home_team:
        raise DeserializationError("Home team is missing from metadata")
    if not away_team:
        raise DeserializationError("Away team is missing from metadata")

    (home_score, away_score,) = match_root.MatchInformation.General.attrib[
        "Result"
    ].split(":")
    score = Score(home=int(home_score), away=int(away_score))
    teams = [home_team, away_team]

    if len(home_team.players) == 0 or len(away_team.players) == 0:
        raise DeserializationError("LineUp incomplete")

    # The periods can be rebuild from event data. Therefore, the periods attribute
    # from the metadata can be ignored. It is required for tracking data.
    other_game_information = (
        match_root.MatchInformation.OtherGameInformation.attrib
    )
    periods = [
        Period(
            id=1,
            start_timestamp=timedelta(
                seconds=SPORTEC_FIRST_HALF_STARTING_FRAME_ID / SPORTEC_FPS
            ),
            end_timestamp=timedelta(
                seconds=SPORTEC_FIRST_HALF_STARTING_FRAME_ID / SPORTEC_FPS
                + float(other_game_information["TotalTimeFirstHalf"]) / 1000
            ),
        ),
        Period(
            id=2,
            start_timestamp=timedelta(
                seconds=SPORTEC_SECOND_HALF_STARTING_FRAME_ID / SPORTEC_FPS
            ),
            end_timestamp=timedelta(
                seconds=SPORTEC_SECOND_HALF_STARTING_FRAME_ID / SPORTEC_FPS
                + float(other_game_information["TotalTimeSecondHalf"]) / 1000
            ),
        ),
    ]

    if "TotalTimeFirstHalfExtra" in other_game_information:
        # Add two periods for extra time.
        periods.extend(
            [
                Period(
                    id=3,
                    start_timestamp=timedelta(
                        seconds=SPORTEC_FIRST_EXTRA_HALF_STARTING_FRAME_ID
                        / SPORTEC_FPS
                    ),
                    end_timestamp=timedelta(
                        seconds=SPORTEC_FIRST_EXTRA_HALF_STARTING_FRAME_ID
                        / SPORTEC_FPS
                        + float(
                            other_game_information["TotalTimeFirstHalfExtra"]
                        )
                        / 1000
                    ),
                ),
                Period(
                    id=4,
                    start_timestamp=timedelta(
                        seconds=SPORTEC_SECOND_EXTRA_HALF_STARTING_FRAME_ID
                        / SPORTEC_FPS
                    ),
                    end_timestamp=timedelta(
                        seconds=SPORTEC_SECOND_EXTRA_HALF_STARTING_FRAME_ID
                        / SPORTEC_FPS
                        + float(
                            other_game_information["TotalTimeSecondHalfExtra"]
                        )
                        / 1000
                    ),
                ),
            ]
        )

    return SportecMetadata(
        score=score,
        teams=teams,
        periods=periods,
        x_max=x_max,
        y_max=y_max,
        fps=SPORTEC_FPS,
    )


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
SPORTEC_EVENT_NAME_OWN_GOAL = "OwnGoal"
SPORTEC_SHOT_EVENT_NAMES = (
    SPORTEC_EVENT_NAME_SHOT_WIDE,
    SPORTEC_EVENT_NAME_SHOT_SAVED,
    SPORTEC_EVENT_NAME_SHOT_BLOCKED,
    SPORTEC_EVENT_NAME_SHOT_WOODWORK,
    SPORTEC_EVENT_NAME_SHOT_OTHER,
    SPORTEC_EVENT_NAME_SHOT_GOAL,
    SPORTEC_EVENT_NAME_OWN_GOAL,
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


def _parse_datetime(dt_str: str) -> datetime:
    return parse(dt_str).astimezone(timezone.utc)


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
    elif event_name == SPORTEC_EVENT_NAME_OWN_GOAL:
        result = ShotResult.OWN_GOAL
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


class SportecEventDataInputs(NamedTuple):
    meta_data: IO[bytes]
    event_data: IO[bytes]


class SportecEventDataDeserializer(
    EventDataDeserializer[SportecEventDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.SPORTEC

    def deserialize(self, inputs: SportecEventDataInputs) -> EventDataset:
        with performance_logging("load data", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())
            event_root = objectify.fromstring(inputs.event_data.read())

        with performance_logging("parse data", logger=logger):
            sportec_metadata = sportec_metadata_from_xml_elm(match_root)
            teams = home_team, away_team = sportec_metadata.teams
            transformer = self.get_transformer(
                pitch_length=sportec_metadata.x_max,
                pitch_width=sportec_metadata.y_max,
            )

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
                        orientation = (
                            Orientation.HOME_AWAY
                            if team_left == home_team.team_id
                            else Orientation.AWAY_HOME
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
                    event = self.event_factory.build_shot(
                        **shot_event_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_name in SPORTEC_PASS_EVENT_NAMES:
                    pass_event_kwargs = _parse_pass(
                        event_chain=event_chain, team=team
                    )
                    event = self.event_factory.build_pass(
                        **pass_event_kwargs,
                        **generic_event_kwargs,
                        receive_timestamp=None,
                        receiver_coordinates=None,
                    )
                elif event_name == SPORTEC_EVENT_NAME_BALL_CLAIMING:
                    event = self.event_factory.build_recovery(
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
                    event = self.event_factory.build_substitution(
                        result=None,
                        qualifiers=None,
                        **substitution_event_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_name == SPORTEC_EVENT_NAME_CAUTION:
                    card_kwargs = _parse_caution(event_attributes)
                    event = self.event_factory.build_card(
                        result=None,
                        qualifiers=None,
                        **card_kwargs,
                        **generic_event_kwargs,
                    )
                elif event_name == SPORTEC_EVENT_NAME_FOUL:
                    foul_kwargs = _parse_foul(event_attributes, teams=teams)
                    generic_event_kwargs.update(foul_kwargs)
                    event = self.event_factory.build_foul_committed(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )
                else:
                    event = self.event_factory.build_generic(
                        result=None,
                        qualifiers=None,
                        event_name=event_name,
                        **generic_event_kwargs,
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
                    out_event = self.event_factory.build_ball_out(
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

        for i, event in enumerate(events[:-1]):
            if (
                event.event_type == EventType.PASS
                and event.result == PassResult.COMPLETE
            ):
                # Sportec uses X/Y-Source-Position to define the start coordinates of
                # an event and X/Y-Position to define the end of an event. There can/will
                # be quite a distance between the start and the end of an event.
                # When we want to set the receiver_coordinates we need to use
                # the start of the event.
                # How to solve this:
                # 1. Create a copy of an event
                # 2. Set the coordinates based on X/Y-Source-Position
                # 3. Pass through the transformer
                # 4. Update the receiver coordinates
                if "X-Source-Position" in events[i + 1].raw_event:
                    updated_event = transformer.transform_event(
                        events[i + 1].replace(
                            coordinates=Point(
                                x=float(
                                    events[i + 1].raw_event[
                                        "X-Source-Position"
                                    ]
                                ),
                                y=float(
                                    events[i + 1].raw_event[
                                        "Y-Source-Position"
                                    ]
                                ),
                            )
                        )
                    )
                    event.receiver_coordinates = updated_event.coordinates
                else:
                    event.receiver_coordinates = events[i + 1].coordinates

        events = list(
            filter(
                self.should_include_event,
                events,
            )
        )

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=sportec_metadata.score,
            frame_rate=None,
            orientation=orientation,
            flags=~(DatasetFlag.BALL_STATE | DatasetFlag.BALL_OWNING_TEAM),
            provider=Provider.SPORTEC,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return EventDataset(
            metadata=metadata,
            records=events,
        )
