import math
from typing import Tuple, Dict, List, NamedTuple, IO, Optional
import logging
from datetime import datetime
import pytz
from lxml import objectify
from lxml.objectify import ObjectifiedElement

from kloppy.domain import (
    EventDataset,
    Team,
    Period,
    Point,
    Point3D,
    BallState,
    DatasetFlag,
    Orientation,
    PassResult,
    ShotResult,
    TakeOnResult,
    DuelResult,
    DuelType,
    DuelQualifier,
    Ground,
    Score,
    Provider,
    Metadata,
    Player,
    Position,
    InterceptionResult,
    FormationType,
    CardType,
    CardQualifier,
    Qualifier,
    SetPieceQualifier,
    SetPieceType,
    BodyPartQualifier,
    BodyPart,
    PassType,
    PassQualifier,
    GoalkeeperQualifier,
    GoalkeeperActionType,
    CounterAttackQualifier,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

EVENT_TYPE_START_PERIOD = 32
EVENT_TYPE_END_PERIOD = 30
EVENT_TYPE_DELETED_EVENT = 43

EVENT_TYPE_PASS = 1
EVENT_TYPE_OFFSIDE_PASS = 2
EVENT_TYPE_TAKE_ON = 3
EVENT_TYPE_TACKLE = 7
EVENT_TYPE_AERIAL = 44
EVENT_TYPE_50_50 = 67
EVENT_TYPE_INTERCEPTION = 8
EVENT_TYPE_CLEARANCE = 12
EVENT_TYPE_SHOT_MISS = 13
EVENT_TYPE_SHOT_POST = 14
EVENT_TYPE_SHOT_SAVED = 15
EVENT_TYPE_SHOT_GOAL = 16
EVENT_TYPE_BALL_OUT = 5
EVENT_TYPE_CORNER_AWARDED = 6
EVENT_TYPE_FOUL_COMMITTED = 4
EVENT_TYPE_CARD = 17
EVENT_TYPE_RECOVERY = 49
EVENT_TYPE_FORMATION_CHANGE = 40
EVENT_TYPE_BALL_TOUCH = 61
EVENT_TYPE_BLOCKED_PASS = 74

EVENT_TYPE_SAVE = 10
EVENT_TYPE_CLAIM = 11
EVENT_TYPE_PUNCH = 41
EVENT_TYPE_KEEPER_PICK_UP = 52
EVENT_TYPE_SMOTHER = 54
KEEPER_EVENTS = [
    EVENT_TYPE_SAVE,
    EVENT_TYPE_CLAIM,
    EVENT_TYPE_PUNCH,
    EVENT_TYPE_KEEPER_PICK_UP,
    EVENT_TYPE_SMOTHER,
]

BALL_OUT_EVENTS = [EVENT_TYPE_BALL_OUT, EVENT_TYPE_CORNER_AWARDED]
DUEL_EVENTS = [
    EVENT_TYPE_TACKLE,
    EVENT_TYPE_AERIAL,
    EVENT_TYPE_50_50,
]

BALL_OWNING_EVENTS = (
    EVENT_TYPE_PASS,
    EVENT_TYPE_OFFSIDE_PASS,
    EVENT_TYPE_TAKE_ON,
    EVENT_TYPE_SHOT_MISS,
    EVENT_TYPE_SHOT_POST,
    EVENT_TYPE_SHOT_SAVED,
    EVENT_TYPE_SHOT_GOAL,
    EVENT_TYPE_RECOVERY,
    EVENT_TYPE_BALL_TOUCH,
)

EVENT_QUALIFIER_GOAL_KICK = 124
EVENT_QUALIFIER_FREE_KICK = 5
EVENT_QUALIFIER_THROW_IN = 107
EVENT_QUALIFIER_CORNER_KICK = 6
EVENT_QUALIFIER_PENALTY = 9
EVENT_QUALIFIER_KICK_OFF = 279
EVENT_QUALIFIER_FREE_KICK_SHOT = 26

EVENT_QUALIFIER_HEAD_PASS = 3
EVENT_QUALIFIER_HEAD = 15
EVENT_QUALIFIER_LEFT_FOOT = 72
EVENT_QUALIFIER_RIGHT_FOOT = 20
EVENT_QUALIFIER_OTHER_BODYPART = 21

EVENT_QUALIFIER_LONG_BALL = 1
EVENT_QUALIFIER_CROSS = 2
EVENT_QUALIFIER_THROUGH_BALL = 4
EVENT_QUALIFIER_CHIPPED_BALL = 155
EVENT_QUALIFIER_LAUNCH = 157
EVENT_QUALIFIER_FLICK_ON = 168
EVENT_QUALIFIER_SWITCH_OF_PLAY = 196
EVENT_QUALIFIER_SHOT_ASSIST = 210
EVENT_QUALIFIER_ASSIST_2ND = 218

EVENT_QUALIFIER_FIRST_YELLOW_CARD = 31
EVENT_QUALIFIER_SECOND_YELLOW_CARD = 32
EVENT_QUALIFIER_RED_CARD = 33

EVENT_QUALIFIER_COUNTER_ATTACK = 23

EVENT_QUALIFIER_TEAM_FORMATION = 130

event_type_names = {
    1: "pass",
    2: "offside pass",
    3: "take on",
    4: "foul",
    5: "out",
    6: "corner awarded",
    7: "tackle",
    8: "interception",
    9: "turnover",
    10: "save",
    11: "claim",
    12: "clearance",
    13: "miss",
    14: "post",
    15: "attempt saved",
    16: "goal",
    17: "card",
    18: "player off",
    19: "player on",
    20: "player retired",
    21: "player returns",
    22: "player becomes goalkeeper",
    23: "goalkeeper becomes player",
    24: "condition change",
    25: "official change",
    26: "unknown26",
    27: "start delay",
    28: "end delay",
    29: "unknown29",
    30: "end",
    31: "unknown31",
    32: "start",
    33: "unknown33",
    34: "team set up",
    35: "player changed position",
    36: "player changed jersey number",
    37: "collection end",
    38: "temp_goal",
    39: "temp_attempt",
    40: "formation change",
    41: "punch",
    42: "good skill",
    43: "deleted event",
    44: "aerial",
    45: "challenge",
    46: "unknown46",
    47: "rescinded card",
    48: "unknown46",
    49: "ball recovery",
    50: "dispossessed",
    51: "error",
    52: "keeper pick-up",
    53: "cross not claimed",
    54: "smother",
    55: "offside provoked",
    56: "shield ball opp",
    57: "foul throw in",
    58: "penalty faced",
    59: "keeper sweeper",
    60: "chance missed",
    61: "ball touch",
    62: "unknown62",
    63: "temp_save",
    64: "resume",
    65: "contentious referee decision",
    66: "possession data",
    67: "50/50",
    68: "referee drop ball",
    69: "failed to block",
    70: "injury time announcement",
    71: "coach setup",
    72: "caught offside",
    73: "other ball contact",
    74: "blocked pass",
    75: "delayed start",
    76: "early end",
    77: "player off pitch",
}

formations = {
    2: FormationType.FOUR_FOUR_TWO,
    3: FormationType.FOUR_ONE_TWO_ONE_TWO,
    4: FormationType.FOUR_THREE_THREE,
    5: FormationType.FOUR_FIVE_ONE,
    6: FormationType.FOUR_FOUR_ONE_ONE,
    7: FormationType.FOUR_ONE_FOUR_ONE,
    8: FormationType.FOUR_TWO_THREE_ONE,
    9: FormationType.FOUR_THREE_TWO_ONE,
    10: FormationType.FIVE_THREE_TWO,
    11: FormationType.FIVE_FOUR_ONE,
    12: FormationType.THREE_FIVE_TWO,
    13: FormationType.THREE_FOUR_THREE,
    14: FormationType.THREE_ONE_THREE_ONE_TWO,
    15: FormationType.FOUR_TWO_TWO_TWO,
    16: FormationType.THREE_FIVE_ONE_ONE,
    17: FormationType.THREE_FOUR_TWO_ONE,
    18: FormationType.THREE_FOUR_ONE_TWO,
    19: FormationType.THREE_ONE_FOUR_TWO,
    20: FormationType.THREE_ONE_TWO_ONE_THREE,
    21: FormationType.FOUR_ONE_THREE_TWO,
    22: FormationType.FOUR_TWO_FOUR_ZERO,
    23: FormationType.FOUR_THREE_ONE_TWO,
    24: FormationType.THREE_TWO_FOUR_ONE,
    25: FormationType.THREE_THREE_THREE_ONE,
}


def _parse_f24_datetime(dt_str: str) -> datetime:
    def zero_pad_milliseconds(timestamp):
        parts = timestamp.split(".")
        return ".".join(parts[:-1] + ["{:03d}".format(int(parts[-1]))])

    dt_str = zero_pad_milliseconds(dt_str)
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=pytz.utc
    )


def _create_periods(match_result_type: str) -> List[Period]:
    if match_result_type == "AfterExtraTime":
        num_periods = 4
    elif match_result_type == "PenaltyShootout":
        num_periods = 5
    else:
        num_periods = 2

    periods = [
        Period(
            id=period_id,
            start_timestamp=None,
            end_timestamp=None,
        )
        for period_id in range(1, num_periods + 1)
    ]

    return periods


def _parse_pass(raw_qualifiers: Dict[int, str], outcome: int) -> Dict:
    if outcome:
        result = PassResult.COMPLETE
    else:
        result = PassResult.INCOMPLETE
    receiver_coordinates = _get_end_coordinates(raw_qualifiers)
    pass_qualifiers = _get_pass_qualifiers(raw_qualifiers)
    overall_qualifiers = _get_event_qualifiers(raw_qualifiers)

    qualifiers = pass_qualifiers + overall_qualifiers

    return dict(
        result=result,
        receiver_coordinates=receiver_coordinates,
        receiver_player=None,
        receive_timestamp=None,
        qualifiers=qualifiers,
    )


def _parse_offside_pass(raw_qualifiers: Dict[int, str]) -> Dict:
    pass_qualifiers = _get_pass_qualifiers(raw_qualifiers)
    overall_qualifiers = _get_event_qualifiers(raw_qualifiers)

    qualifiers = pass_qualifiers + overall_qualifiers

    return dict(
        result=PassResult.OFFSIDE,
        receiver_coordinates=_get_end_coordinates(raw_qualifiers),
        receiver_player=None,
        receive_timestamp=None,
        qualifiers=qualifiers,
    )


def _parse_take_on(outcome: int) -> Dict:
    if outcome:
        result = TakeOnResult.COMPLETE
    else:
        result = TakeOnResult.INCOMPLETE
    return dict(result=result)


def _parse_clearance(raw_qualifiers: Dict[int, str]) -> Dict:
    return dict(qualifiers=_get_event_qualifiers(raw_qualifiers))


def _parse_card(raw_qualifiers: Dict[int, str]) -> Dict:
    qualifiers = _get_event_qualifiers(raw_qualifiers)

    if EVENT_QUALIFIER_RED_CARD in qualifiers:
        card_type = CardType.RED
    elif EVENT_QUALIFIER_FIRST_YELLOW_CARD in qualifiers:
        card_type = CardType.FIRST_YELLOW
    elif EVENT_QUALIFIER_SECOND_YELLOW_CARD in qualifiers:
        card_type = CardType.SECOND_YELLOW
    else:
        card_type = None

    return dict(result=None, qualifiers=qualifiers, card_type=card_type)


def _parse_formation_change(raw_qualifiers: Dict[int, str]) -> Dict:
    formation_id = int(raw_qualifiers[EVENT_QUALIFIER_TEAM_FORMATION])
    formation = formations[formation_id]

    return dict(formation_type=formation)


def _parse_shot(
    raw_qualifiers: Dict[int, str], type_id: int, coordinates: Point
) -> Dict:
    if type_id == EVENT_TYPE_SHOT_GOAL:
        if 28 in raw_qualifiers:
            coordinates = Point(x=100 - coordinates.x, y=100 - coordinates.y)
            result = ShotResult.OWN_GOAL
            # ball_owning_team =
            # timestamp =
        else:
            result = ShotResult.GOAL
    elif 82 in raw_qualifiers:
        result = ShotResult.BLOCKED
    elif type_id == EVENT_TYPE_SHOT_MISS:
        result = ShotResult.OFF_TARGET
    elif type_id == EVENT_TYPE_SHOT_POST:
        result = ShotResult.OFF_TARGET
    elif type_id == EVENT_TYPE_SHOT_SAVED:
        result = ShotResult.SAVED
    else:
        result = None

    qualifiers = _get_event_qualifiers(raw_qualifiers)
    result_coordinates = _get_end_coordinates(
        raw_qualifiers, start_coordinates=coordinates
    )
    if result == ShotResult.OWN_GOAL:
        if isinstance(result_coordinates, Point3D):
            result_coordinates = Point3D(
                x=100 - result_coordinates.x,
                y=100 - result_coordinates.y,
                z=result_coordinates.z,
            )
        elif isinstance(result_coordinates, Point):
            result_coordinates = Point(
                x=100 - result_coordinates.x,
                y=100 - result_coordinates.y,
            )

    return dict(
        coordinates=coordinates,
        result=result,
        result_coordinates=result_coordinates,
        qualifiers=qualifiers,
    )


def _parse_goalkeeper_events(
    raw_qualifiers: Dict[int, str], type_id: int
) -> Dict:
    qualifiers = _get_event_qualifiers(raw_qualifiers)
    goalkeeper_qualifiers = _get_goalkeeper_qualifiers(type_id)
    qualifiers.extend(goalkeeper_qualifiers)

    return dict(result=None, qualifiers=qualifiers)


def _parse_duel(
    raw_qualifiers: Dict[int, str], type_id: int, outcome: int
) -> Dict:
    qualifiers = _get_event_qualifiers(raw_qualifiers)
    if type_id == EVENT_TYPE_TACKLE:
        qualifiers.extend([DuelQualifier(value=DuelType.GROUND)])
    elif type_id == EVENT_TYPE_AERIAL:
        qualifiers.extend(
            [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=DuelType.AERIAL),
            ]
        )
    elif type_id == EVENT_TYPE_50_50:
        qualifiers.extend(
            [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=DuelType.GROUND),
            ]
        )

    result = DuelResult.WON if outcome else DuelResult.LOST

    return dict(
        result=result,
        qualifiers=qualifiers,
    )


def _parse_interception(
    raw_qualifiers: Dict[int, str], team: Team, next_event: ObjectifiedElement
) -> Dict:
    qualifiers = _get_event_qualifiers(raw_qualifiers)
    result = InterceptionResult.SUCCESS

    if next_event is not None:
        next_event_type_id = int(next_event.attrib["type_id"])
        if next_event_type_id in BALL_OUT_EVENTS:
            result = InterceptionResult.OUT
        elif (next_event_type_id in BALL_OWNING_EVENTS) and (
            next_event.attrib["team_id"] != team.team_id
        ):
            result = InterceptionResult.LOST

    return dict(
        result=result,
        qualifiers=qualifiers,
    )


def _parse_team_players(
    f7_root, team_ref: str
) -> Tuple[str, Dict[str, Dict[str, str]]]:
    matchdata_path = objectify.ObjectPath("SoccerFeed.SoccerDocument")
    team_elms = list(matchdata_path.find(f7_root).iterchildren("Team"))
    for team_elm in team_elms:
        if team_elm.attrib["uID"] == team_ref:
            team_name = str(team_elm.find("Name"))
            players = {
                player_elm.attrib["uID"]: dict(
                    first_name=str(
                        player_elm.find("PersonName").find("First")
                    ),
                    last_name=str(player_elm.find("PersonName").find("Last")),
                )
                for player_elm in team_elm.iterchildren("Player")
            }
            break
    else:
        raise DeserializationError(f"Could not parse players for {team_ref}")

    return team_name, players


def _team_from_xml_elm(team_elm, f7_root) -> Team:
    # This should not happen here
    team_name, team_players = _parse_team_players(
        f7_root, team_elm.attrib["TeamRef"]
    )

    team_id = team_elm.attrib["TeamRef"].lstrip("t")
    formation = "-".join(list(team_elm.attrib["Formation"]))
    team = Team(
        team_id=str(team_id),
        name=team_name,
        ground=Ground.HOME
        if team_elm.attrib["Side"] == "Home"
        else Ground.AWAY,
        starting_formation=FormationType(formation),
    )
    team.players = [
        Player(
            player_id=player_elm.attrib["PlayerRef"].lstrip("p"),
            team=team,
            jersey_no=int(player_elm.attrib["ShirtNumber"]),
            first_name=team_players[player_elm.attrib["PlayerRef"]][
                "first_name"
            ],
            last_name=team_players[player_elm.attrib["PlayerRef"]][
                "last_name"
            ],
            starting=True if player_elm.attrib["Status"] == "Start" else False,
            position=Position(
                position_id=player_elm.attrib["Formation_Place"],
                name=player_elm.attrib["Position"],
                coordinates=None,
            ),
        )
        for player_elm in team_elm.find("PlayerLineUp").iterchildren(
            "MatchPlayer"
        )
    ]
    return team


def _get_end_coordinates(
    raw_qualifiers: Dict[int, str], start_coordinates: Optional[Point] = None
) -> Optional[Point]:
    x, y, z = None, None, None

    # pass
    if 140 in raw_qualifiers and 141 in raw_qualifiers:
        x = float(raw_qualifiers[140])
        y = float(raw_qualifiers[141])

    # blocked shot
    elif 146 in raw_qualifiers and 147 in raw_qualifiers:
        x = float(raw_qualifiers[146])
        y = float(raw_qualifiers[147])
        if 102 in raw_qualifiers and 103 in raw_qualifiers:
            # the goal mouth z-coordinate is projected back to the location
            # where the shot was blocked
            assert start_coordinates is not None
            x0, y0 = start_coordinates.x, start_coordinates.y
            x_proj = float(100)
            y_proj = float(raw_qualifiers[102])
            z_proj = float(raw_qualifiers[103])
            adj_proj = math.sqrt((x_proj - x0) ** 2 + (y_proj - y0) ** 2)
            adj_block = math.sqrt((x - x0) ** 2 + (y - y0) ** 2)
            z = z_proj / adj_proj * adj_block

    # passed the goal line
    elif 102 in raw_qualifiers:
        x = float(100)
        y = float(raw_qualifiers[102])
        if 103 in raw_qualifiers:
            z = float(raw_qualifiers[103])

    if x is not None and y is not None and z is not None:
        return Point3D(x=x, y=y, z=z)
    if x is not None and y is not None:
        return Point(x=x, y=y)

    return None


def _get_event_qualifiers(raw_qualifiers: Dict[int, str]) -> List[Qualifier]:
    qualifiers = []
    qualifiers.extend(_get_event_setpiece_qualifiers(raw_qualifiers))
    qualifiers.extend(_get_event_bodypart_qualifiers(raw_qualifiers))
    qualifiers.extend(_get_event_card_qualifiers(raw_qualifiers))
    qualifiers.extend(_get_event_counter_attack_qualifiers(raw_qualifiers))
    return qualifiers


def _get_pass_qualifiers(raw_qualifiers: Dict[int, str]) -> List[Qualifier]:
    qualifiers = []
    pass_qualifier_mapping = {
        EVENT_QUALIFIER_CROSS: PassType.CROSS,
        EVENT_QUALIFIER_LONG_BALL: PassType.LONG_BALL,
        EVENT_QUALIFIER_CHIPPED_BALL: PassType.CHIPPED_PASS,
        EVENT_QUALIFIER_THROUGH_BALL: PassType.THROUGH_BALL,
        EVENT_QUALIFIER_LAUNCH: PassType.LAUNCH,
        EVENT_QUALIFIER_FLICK_ON: PassType.FLICK_ON,
        EVENT_QUALIFIER_ASSIST_2ND: PassType.ASSIST_2ND,
    }
    for (
        sp_pass_qualifier,
        pass_qualifier_value,
    ) in pass_qualifier_mapping.items():
        if sp_pass_qualifier in raw_qualifiers:
            qualifiers.append(PassQualifier(value=pass_qualifier_value))

    if EVENT_QUALIFIER_SHOT_ASSIST in raw_qualifiers:
        qualifiers.append(PassQualifier(value=PassType.SHOT_ASSIST))
        shot_result_qualifier = int(
            raw_qualifiers[EVENT_QUALIFIER_SHOT_ASSIST]
        )
        if shot_result_qualifier == EVENT_TYPE_SHOT_GOAL:
            qualifiers.append(PassQualifier(value=PassType.ASSIST))

    return qualifiers


def _get_event_setpiece_qualifiers(
    raw_qualifiers: Dict[int, str]
) -> List[Qualifier]:
    qualifiers = []
    if EVENT_QUALIFIER_CORNER_KICK in raw_qualifiers:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.CORNER_KICK))
    elif (
        EVENT_QUALIFIER_FREE_KICK in raw_qualifiers
        or EVENT_QUALIFIER_FREE_KICK_SHOT in raw_qualifiers
    ):
        qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))
    elif EVENT_QUALIFIER_PENALTY in raw_qualifiers:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.PENALTY))
    elif EVENT_QUALIFIER_THROW_IN in raw_qualifiers:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.THROW_IN))
    elif EVENT_QUALIFIER_KICK_OFF in raw_qualifiers:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.KICK_OFF))
    elif EVENT_QUALIFIER_GOAL_KICK in raw_qualifiers:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.GOAL_KICK))
    return qualifiers


def _get_event_bodypart_qualifiers(
    raw_qualifiers: Dict[int, str]
) -> List[Qualifier]:
    qualifiers = []
    if EVENT_QUALIFIER_HEAD_PASS in raw_qualifiers:
        qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))
    elif EVENT_QUALIFIER_HEAD in raw_qualifiers:
        qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))
    elif EVENT_QUALIFIER_LEFT_FOOT in raw_qualifiers:
        qualifiers.append(BodyPartQualifier(value=BodyPart.LEFT_FOOT))
    elif EVENT_QUALIFIER_RIGHT_FOOT in raw_qualifiers:
        qualifiers.append(BodyPartQualifier(value=BodyPart.RIGHT_FOOT))
    elif EVENT_QUALIFIER_OTHER_BODYPART in raw_qualifiers:
        qualifiers.append(BodyPartQualifier(value=BodyPart.OTHER))
    return qualifiers


def _get_event_card_qualifiers(
    raw_qualifiers: Dict[int, str]
) -> List[Qualifier]:
    qualifiers = []
    if EVENT_QUALIFIER_RED_CARD in raw_qualifiers:
        qualifiers.append(CardQualifier(value=CardType.RED))
    elif EVENT_QUALIFIER_FIRST_YELLOW_CARD in raw_qualifiers:
        qualifiers.append(CardQualifier(value=CardType.FIRST_YELLOW))
    elif EVENT_QUALIFIER_SECOND_YELLOW_CARD in raw_qualifiers:
        qualifiers.append(CardQualifier(value=CardType.SECOND_YELLOW))

    return qualifiers


def _get_goalkeeper_qualifiers(type_id: int) -> List[Qualifier]:
    qualifiers = []
    goalkeeper_qualifier = None
    if type_id == EVENT_TYPE_SAVE:
        goalkeeper_qualifier = GoalkeeperActionType.SAVE
    elif type_id == EVENT_TYPE_CLAIM:
        goalkeeper_qualifier = GoalkeeperActionType.CLAIM
    elif type_id == EVENT_TYPE_PUNCH:
        goalkeeper_qualifier = GoalkeeperActionType.PUNCH
    elif type_id == EVENT_TYPE_KEEPER_PICK_UP:
        goalkeeper_qualifier = GoalkeeperActionType.PICK_UP
    elif type_id == EVENT_TYPE_SMOTHER:
        goalkeeper_qualifier = GoalkeeperActionType.SMOTHER

    if goalkeeper_qualifier:
        qualifiers.append(GoalkeeperQualifier(value=goalkeeper_qualifier))

    return qualifiers


def _get_event_counter_attack_qualifiers(
    raw_qualifiers: Dict[int, str],
) -> List[Qualifier]:
    qualifiers = []
    if EVENT_QUALIFIER_COUNTER_ATTACK in raw_qualifiers:
        qualifiers.append(CounterAttackQualifier(True))

    return qualifiers


def _get_event_type_name(type_id: int) -> str:
    return event_type_names.get(type_id, "unknown")


class OptaInputs(NamedTuple):
    f7_data: IO[bytes]
    f24_data: IO[bytes]


class OptaDeserializer(EventDataDeserializer[OptaInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.OPTA

    def deserialize(self, inputs: OptaInputs) -> EventDataset:
        transformer = self.get_transformer()

        with performance_logging("load data", logger=logger):
            f7_root = objectify.fromstring(inputs.f7_data.read())
            f24_root = objectify.fromstring(inputs.f24_data.read())

        with performance_logging("parse data", logger=logger):
            matchdata_path = objectify.ObjectPath(
                "SoccerFeed.SoccerDocument.MatchData"
            )
            match_result_path = objectify.ObjectPath(
                "SoccerFeed.SoccerDocument.MatchData.MatchInfo.Result"
            )
            team_elms = list(
                matchdata_path.find(f7_root).iterchildren("TeamData")
            )

            home_score = None
            away_score = None
            for team_elm in team_elms:
                if team_elm.attrib["Side"] == "Home":
                    home_score = int(team_elm.attrib["Score"])
                    home_team = _team_from_xml_elm(team_elm, f7_root)
                elif team_elm.attrib["Side"] == "Away":
                    away_score = int(team_elm.attrib["Score"])
                    away_team = _team_from_xml_elm(team_elm, f7_root)
                else:
                    raise DeserializationError(
                        f"Unknown side: {team_elm.attrib['Side']}"
                    )
            score = Score(home=home_score, away=away_score)
            teams = [home_team, away_team]
            match_result_type = list(match_result_path.find(f7_root))[
                0
            ].attrib["Type"]
            periods = _create_periods(match_result_type)

            if len(home_team.players) == 0 or len(away_team.players) == 0:
                raise DeserializationError("LineUp incomplete")

            game_elm = f24_root.find("Game")

            possession_team = None
            events = []
            events_list = [
                event
                for event in list(game_elm.iterchildren("Event"))
                if int(event.attrib["type_id"]) != EVENT_TYPE_DELETED_EVENT
            ]
            for idx, event_elm in enumerate(events_list):
                next_event_elm = (
                    events_list[idx + 1]
                    if (idx + 1) < len(events_list)
                    else None
                )
                event_id = event_elm.attrib["id"]
                type_id = int(event_elm.attrib["type_id"])
                timestamp = _parse_f24_datetime(event_elm.attrib["timestamp"])
                period_id = int(event_elm.attrib["period_id"])
                for period in periods:
                    if period.id == period_id:
                        break
                else:
                    logger.debug(
                        f"Skipping event {event_id} because period doesn't match {period_id}"
                    )
                    continue

                if type_id == EVENT_TYPE_START_PERIOD:
                    logger.debug(
                        f"Set start of period {period.id} to {timestamp}"
                    )
                    period.start_timestamp = timestamp
                elif type_id == EVENT_TYPE_END_PERIOD:
                    logger.debug(
                        f"Set end of period {period.id} to {timestamp}"
                    )
                    period.end_timestamp = timestamp
                else:
                    if not period.start_timestamp:
                        # not started yet
                        continue

                    if event_elm.attrib["team_id"] == home_team.team_id:
                        team = teams[0]
                    elif event_elm.attrib["team_id"] == away_team.team_id:
                        team = teams[1]
                    else:
                        raise DeserializationError(
                            f"Unknown team_id {event_elm.attrib['team_id']}"
                        )

                    x = float(event_elm.attrib["x"])
                    y = float(event_elm.attrib["y"])
                    outcome = int(event_elm.attrib["outcome"])
                    raw_qualifiers = {
                        int(
                            qualifier_elm.attrib["qualifier_id"]
                        ): qualifier_elm.attrib.get("value")
                        for qualifier_elm in event_elm.iterchildren("Q")
                    }
                    player = None
                    if "player_id" in event_elm.attrib:
                        player = team.get_player_by_id(
                            event_elm.attrib["player_id"]
                        )

                    if type_id in BALL_OWNING_EVENTS:
                        possession_team = team

                    generic_event_kwargs = dict(
                        # from DataRecord
                        period=period,
                        timestamp=timestamp - period.start_timestamp,
                        ball_owning_team=possession_team,
                        ball_state=BallState.ALIVE,
                        # from Event
                        event_id=event_id,
                        team=team,
                        player=player,
                        coordinates=Point(x=x, y=y),
                        raw_event=event_elm,
                    )

                    if type_id == EVENT_TYPE_PASS:
                        pass_event_kwargs = _parse_pass(
                            raw_qualifiers, outcome
                        )
                        event = self.event_factory.build_pass(
                            **pass_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_OFFSIDE_PASS:
                        pass_event_kwargs = _parse_offside_pass(raw_qualifiers)
                        event = self.event_factory.build_pass(
                            **pass_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_TAKE_ON:
                        take_on_event_kwargs = _parse_take_on(outcome)
                        event = self.event_factory.build_take_on(
                            **take_on_event_kwargs,
                            **generic_event_kwargs,
                            qualifiers=None,
                        )
                    elif type_id in (
                        EVENT_TYPE_SHOT_MISS,
                        EVENT_TYPE_SHOT_POST,
                        EVENT_TYPE_SHOT_SAVED,
                        EVENT_TYPE_SHOT_GOAL,
                    ):
                        if type_id == EVENT_TYPE_SHOT_GOAL:
                            if 374 in raw_qualifiers.keys():
                                generic_event_kwargs["timestamp"] = (
                                    _parse_f24_datetime(
                                        raw_qualifiers.get(374).replace(
                                            " ", "T"
                                        )
                                    )
                                    - period.start_timestamp
                                )
                        shot_event_kwargs = _parse_shot(
                            raw_qualifiers,
                            type_id,
                            coordinates=generic_event_kwargs["coordinates"],
                        )
                        kwargs = {}
                        kwargs.update(generic_event_kwargs)
                        kwargs.update(shot_event_kwargs)
                        event = self.event_factory.build_shot(**kwargs)
                    elif type_id == EVENT_TYPE_RECOVERY:
                        event = self.event_factory.build_recovery(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_CLEARANCE:
                        clearance_event_kwargs = _parse_clearance(
                            raw_qualifiers
                        )
                        event = self.event_factory.build_clearance(
                            result=None,
                            **clearance_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif type_id in DUEL_EVENTS:
                        duel_event_kwargs = _parse_duel(
                            raw_qualifiers, type_id, outcome
                        )
                        event = self.event_factory.build_duel(
                            **duel_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif type_id in (
                        EVENT_TYPE_INTERCEPTION,
                        EVENT_TYPE_BLOCKED_PASS,
                    ):
                        interception_event_kwargs = _parse_interception(
                            raw_qualifiers, team, next_event_elm
                        )
                        event = self.event_factory.build_interception(
                            **interception_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif type_id in KEEPER_EVENTS:
                        goalkeeper_event_kwargs = _parse_goalkeeper_events(
                            raw_qualifiers, type_id
                        )
                        event = self.event_factory.build_goalkeeper_event(
                            **goalkeeper_event_kwargs, **generic_event_kwargs
                        )
                    elif (type_id == EVENT_TYPE_BALL_TOUCH) & (outcome == 0):
                        event = self.event_factory.build_miscontrol(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )
                    elif (type_id == EVENT_TYPE_FOUL_COMMITTED) and (
                        outcome == 0
                    ):
                        event = self.event_factory.build_foul_committed(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )
                    elif type_id in BALL_OUT_EVENTS:
                        generic_event_kwargs["ball_state"] = BallState.DEAD
                        event = self.event_factory.build_ball_out(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_FORMATION_CHANGE:
                        formation_change_event_kwargs = (
                            _parse_formation_change(raw_qualifiers)
                        )
                        event = self.event_factory.build_formation_change(
                            result=None,
                            qualifiers=None,
                            **formation_change_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif type_id == EVENT_TYPE_CARD:
                        generic_event_kwargs["ball_state"] = BallState.DEAD
                        card_event_kwargs = _parse_card(raw_qualifiers)

                        event = self.event_factory.build_card(
                            **card_event_kwargs,
                            **generic_event_kwargs,
                        )
                    else:
                        event = self.event_factory.build_generic(
                            **generic_event_kwargs,
                            result=None,
                            qualifiers=None,
                            event_name=_get_event_type_name(type_id),
                        )

                    if self.should_include_event(event):
                        events.append(transformer.transform_event(event))

        metadata = Metadata(
            teams=teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=score,
            frame_rate=None,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM | DatasetFlag.BALL_STATE,
            provider=Provider.OPTA,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return EventDataset(
            metadata=metadata,
            records=events,
        )
