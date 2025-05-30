import json
import logging
from datetime import timedelta
from typing import Dict, List, Tuple, NamedTuple, IO, Optional

from kloppy.domain import (
    BallOutEvent,
    BodyPart,
    BodyPartQualifier,
    CardEvent,
    CardType,
    CounterAttackQualifier,
    Dimension,
    DuelType,
    DuelQualifier,
    DuelResult,
    EventDataset,
    FoulCommittedEvent,
    GenericEvent,
    GoalkeeperQualifier,
    GoalkeeperActionType,
    Ground,
    InterceptionResult,
    Metadata,
    Orientation,
    PassEvent,
    PassQualifier,
    PassResult,
    PassType,
    Period,
    PitchDimensions,
    Player,
    Point,
    Point3D,
    Provider,
    Qualifier,
    RecoveryEvent,
    SetPieceQualifier,
    SetPieceType,
    ShotEvent,
    ShotResult,
    TakeOnEvent,
    TakeOnResult,
    Team,
    FormationType,
    Score,
    BallState,
    PositionType,
)
from kloppy.exceptions import DeserializationError
from kloppy.utils import performance_logging

from ..deserializer import EventDataDeserializer

FORMATIONS = {
    111: FormationType.FOUR_ONE_FOUR_ONE,
    106: FormationType.THREE_FIVE_TWO,
    105: FormationType.THREE_FIVE_TWO,
    103: FormationType.THREE_THREE_THREE_ONE,
    96: FormationType.FOUR_FOUR_TWO,
    90: FormationType.THREE_FOUR_THREE,
    82: FormationType.FOUR_TWO_THREE_ONE,
    16: FormationType.FOUR_FOUR_TWO,
    3: FormationType.FOUR_THREE_THREE,
}

POSITIONS = {
    4: PositionType.Goalkeeper,  # GK
    5: PositionType.LeftCenterBack,  # LCD
    6: PositionType.RightCenterBack,  # RCD
    7: PositionType.RightBack,  # RD
    8: PositionType.LeftBack,  # LD
    9: PositionType.LeftCentralMidfield,  # LCM
    10: PositionType.CenterDefensiveMidfield,  # CDM
    11: PositionType.RightCentralMidfield,  # RCM
    12: PositionType.Striker,  # CF
    13: PositionType.LeftAttackingMidfield,  # LAM
    14: PositionType.RightAttackingMidfield,  # RAM
    # 15: None,  # Substitute Player
    17: PositionType.CenterAttackingMidfield,  # CAM
    18: PositionType.RightMidfield,  # RM
    19: PositionType.LeftMidfield,  # LM
    20: PositionType.Striker,  # LCF
    21: PositionType.Striker,  # RCF
    83: PositionType.RightDefensiveMidfield,  # RCDM
    84: PositionType.LeftDefensiveMidfield,  # LCDM
    91: PositionType.RightDefensiveMidfield,  # RDM
    92: PositionType.LeftAttackingMidfield,  # LCAM
    93: PositionType.CenterBack,  # CB
    94: PositionType.RightAttackingMidfield,  # RCAM
    95: PositionType.LeftDefensiveMidfield,  # LDM
    112: PositionType.CentralMidfield,  # CM
    198: PositionType.LeftForward,  # LF
    199: PositionType.RightForward,  # RF
}

BODY_PARTS = {
    1: BodyPart.RIGHT_FOOT,
    2: BodyPart.LEFT_FOOT,
    3: BodyPart.HEAD,
    4: BodyPart.OTHER,
    5: BodyPart.OTHER,
}
SET_PIECES = {
    1: None,  # Open-play
    2: SetPieceType.THROW_IN,
    3: SetPieceType.FREE_KICK,  # Indirect free kick
    4: SetPieceType.FREE_KICK,  # Free-kick attack
    5: SetPieceType.CORNER_KICK,
    6: SetPieceType.PENALTY,
    7: None,  # Broadcast interruption
    8: SetPieceType.GOAL_KICK,
}

FIRST_HALF = 1
ACCURATE_PASS = 2
BALL_RECEIVING = 25
INACCURATE_PASS = 26
LOST_BALL = 27
PASS_INTERCEPTION = 28
RECOVERED_BALL = 29
AERIAL_DUEL = 30
BALL_OUT_OF_THE_FIELD = 33
DUEL = 34
PICKING_UP = 35
INACCURATE_KEY_PASS = 36
TACKLE = 38
DRIBBLING = 39
INACCURATE_CROSS = 40
GK_INTERCEPTION_PLUS = 41
SHOT_WIDE = 44
DRIBBLE_PAST_OPPONENT_MINUS = 45
OFFSIDE = 47
CREATED_OFFSIDE_TRAP = 48
DRIBBLE_PAST_OPPONENT_PLUS = 50
FOUL = 51
BAD_BALL_CONTROL = 52
BLOCKED_SHOT = 53
YELLOW_CARD = 55
ACCURATE_CROSS = 57
ACCURATE_KEY_PASS = 58
GS_OPP_CREATED = 59
GRAVE_MISTAKE = 61
GK_INTERCEPTION_MINUS = 62
GS_OPP_NOT_SCORED = 63
GS_OPPORTUNITY_MINUS = 64
GOAL = 65
GS_OPPORTUNITY_PLUS = 66
GS_OPP_SCORED = 68
GRAVE_GOAL_MISTAKE = 69
SHOT_ON_TARGET = 70
EFFECTIVE_SAVE = 71
CROSS_INTERCEPTION = 73
HALF_TIME = 74
SECOND_HALF = 75
SUBSTITUTION = 77
ASSIST = 79
FIRST_HALF_ADDITIONAL_TIME_START = 81
SECOND_HALF_ADDITIONAL_TIME_START = 85
RED_CARD = 86
MATCH_END = 89
SHOT_INTO_THE_BAR_POST = 97
BLOCKED_SHOT_BY_FIELD_PLAYER = 98
OWN_GOAL = 100
CROSS = 104
CLEARANCE = 115
TOUCH = 130
KEY_PASS_INTERCEPTION = 201
PASS_INTO_DUEL_PLUS = 202
PASS_INTO_DUEL_MINUS = 203
BOUNCING_SAVE_PLUS = 204
BOUNCING_SAVE_MINUS = 205
YELLOW_RED_CARD = 206

ACTION_IDS_TO_IGNORE = (
    [
        FIRST_HALF,
        RECOVERED_BALL,
        DRIBBLING,
        GS_OPP_CREATED,
        GS_OPP_NOT_SCORED,
        GS_OPPORTUNITY_MINUS,
        GS_OPPORTUNITY_PLUS,
        GS_OPP_SCORED,
        HALF_TIME,
        SECOND_HALF,
        FIRST_HALF_ADDITIONAL_TIME_START,
        SECOND_HALF_ADDITIONAL_TIME_START,
        MATCH_END,
        BALL_OUT_OF_THE_FIELD,
        LOST_BALL,
        CREATED_OFFSIDE_TRAP,
        BLOCKED_SHOT_BY_FIELD_PLAYER,
        BALL_RECEIVING,
    ]
    + list(FORMATIONS.keys())
    + list(POSITIONS.keys())
)
ACTION_IDS_TO_IGNORE += [TOUCH]

PASS_IDS = [
    ACCURATE_PASS,
    INACCURATE_PASS,
    ACCURATE_KEY_PASS,
    INACCURATE_KEY_PASS,
    CROSS,
    ACCURATE_CROSS,
    INACCURATE_CROSS,
    PASS_INTO_DUEL_PLUS,
    PASS_INTO_DUEL_MINUS,
    ASSIST,
]
PASS_ACCURATE_IDS = [
    ACCURATE_PASS,
    ACCURATE_KEY_PASS,
    ACCURATE_CROSS,
    PASS_INTO_DUEL_PLUS,
]
PASS_INACCURATE_IDS = [
    INACCURATE_PASS,
    INACCURATE_KEY_PASS,
    INACCURATE_CROSS,
    PASS_INTO_DUEL_MINUS,
]
CROSS_IDS = [CROSS, ACCURATE_CROSS, INACCURATE_CROSS]
SHOT_IDS = [
    SHOT_WIDE,
    BLOCKED_SHOT,
    GOAL,
    SHOT_ON_TARGET,
    SHOT_INTO_THE_BAR_POST,
    OWN_GOAL,
]
TWO_PEOPLE_DUEL_IDS = [AERIAL_DUEL, DUEL]
TAKE_ON_IDS = [
    DRIBBLING,
    DRIBBLE_PAST_OPPONENT_PLUS,
    DRIBBLE_PAST_OPPONENT_MINUS,
]
INTERCEPTION_IDS = [
    PASS_INTERCEPTION,
    CROSS_INTERCEPTION,
    KEY_PASS_INTERCEPTION,
]
GOALKEEPER_IDS = [
    GK_INTERCEPTION_PLUS,
    GK_INTERCEPTION_MINUS,
    EFFECTIVE_SAVE,
    BOUNCING_SAVE_PLUS,
    BOUNCING_SAVE_MINUS,
]
CARD_IDS = [YELLOW_CARD, RED_CARD, YELLOW_RED_CARD]
FOUL_IDS = [FOUL, OFFSIDE]

BALL_OWNING_IDS = PASS_IDS + TAKE_ON_IDS + SHOT_IDS

LINEUP_INFORMATION_EVENTS = (
    list(FORMATIONS.keys()) + list(POSITIONS.keys()) + [FIRST_HALF]
)

logger = logging.getLogger(__name__)


class SmrtStatsInputs(NamedTuple):
    raw_data: IO[bytes]
    pitch_length: Optional[float] = None
    pitch_width: Optional[float] = None


def _get_event_set_piece_qualifier(
    set_piece_id: Optional[int],
) -> List[SetPieceQualifier]:
    return (
        [SetPieceQualifier(value=SET_PIECES[set_piece_id])]
        if SET_PIECES.get(set_piece_id)
        else []
    )


def _get_event_body_part_qualifier(
    body_part_id: Optional[int],
) -> List[BodyPartQualifier]:
    return (
        [BodyPartQualifier(value=BODY_PARTS[body_part_id])]
        if BODY_PARTS.get(body_part_id)
        else []
    )


def _get_event_qualifiers(raw_event: Dict) -> List[Qualifier]:
    set_piece_qualifiers = _get_event_set_piece_qualifier(
        raw_event["set_piece_id"]
    )
    body_part_qualifiers = _get_event_body_part_qualifier(
        raw_event["body_part_id"]
    )

    return set_piece_qualifiers + body_part_qualifiers


def _parse_take_on(raw_event: Dict, action_id: int) -> Dict:
    if action_id == DRIBBLE_PAST_OPPONENT_PLUS:
        result = TakeOnResult.COMPLETE
    elif action_id == DRIBBLE_PAST_OPPONENT_MINUS:
        result = TakeOnResult.INCOMPLETE
    else:
        result = None

    return dict(result=result, qualifiers=_get_event_qualifiers(raw_event))


def _parse_card(raw_event: Dict, action_id: int) -> Dict:
    qualifiers = _get_event_qualifiers(raw_event)

    if action_id == RED_CARD:
        card_type = CardType.RED
    elif action_id == YELLOW_CARD:
        card_type = CardType.FIRST_YELLOW
    elif action_id == YELLOW_RED_CARD:
        card_type = CardType.SECOND_YELLOW
    else:
        card_type = None

    return dict(result=None, qualifiers=qualifiers, card_type=card_type)


#
#
# def _parse_formation_change(raw_qualifiers: Dict[int, str]) -> Dict:
#     formation_id = int(raw_qualifiers[EVENT_QUALIFIER_TEAM_FORMATION])
#     formation = formations[formation_id]
#
#     return dict(formation_type=formation)


def _parse_shot(raw_event: Dict, action_id: int) -> Dict:
    result = None
    if action_id == OWN_GOAL:
        # Check whether own goal is marked at right position (diff from Opta)
        result = ShotResult.OWN_GOAL
    elif action_id == GOAL:
        result = ShotResult.GOAL
    elif action_id in [BLOCKED_SHOT, BLOCKED_SHOT_BY_FIELD_PLAYER]:
        result = ShotResult.BLOCKED
    elif action_id in [SHOT_WIDE, SHOT_INTO_THE_BAR_POST]:
        result = ShotResult.OFF_TARGET
    elif action_id == SHOT_ON_TARGET:
        result = ShotResult.SAVED

    qualifiers = _get_event_qualifiers(raw_event)
    if (
        result == ShotResult.BLOCKED
        or raw_event["gate_coord_x"] is None
        or raw_event["gate_coord_y"] is None
    ):
        result_coordinates = None
    else:
        result_coordinates = Point3D(
            x=105,
            y=34 + raw_event["gate_coord_x"],
            z=raw_event["gate_coord_y"],
        )

    return dict(
        result=result,
        result_coordinates=result_coordinates,
        qualifiers=qualifiers,
    )


def _get_goalkeeper_qualifiers(action_id: int) -> List[GoalkeeperQualifier]:
    if action_id == PICKING_UP:
        return [GoalkeeperQualifier(value=GoalkeeperActionType.PICK_UP)]
    elif action_id in [
        EFFECTIVE_SAVE,
        BOUNCING_SAVE_PLUS,
        BOUNCING_SAVE_MINUS,
    ]:
        return [GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)]
    elif action_id in [GK_INTERCEPTION_PLUS, GK_INTERCEPTION_MINUS]:
        return [GoalkeeperQualifier(value=GoalkeeperActionType.CLAIM)]
    else:
        return []


def _parse_goalkeeper_events(raw_event: Dict, action_id: int) -> Dict:
    goalkeeper_qualifiers = _get_goalkeeper_qualifiers(action_id)
    overall_qualifiers = _get_event_qualifiers(raw_event)
    qualifiers = goalkeeper_qualifiers + overall_qualifiers

    return dict(result=None, qualifiers=qualifiers)


def _update_recipient_event_kwargs(
    generic_event_kwargs: Dict,
    raw_event: Dict,
    home_team: Team,
    away_team: Team,
) -> Dict:
    recipient_event_kwargs = generic_event_kwargs.copy()
    home_recipient_player = home_team.get_player_by_id(
        str(raw_event["recipient_id"])
    )
    away_recipient_player = away_team.get_player_by_id(
        str(raw_event["recipient_id"])
    )
    if home_recipient_player:
        recipient_event_kwargs["player"] = home_recipient_player
        recipient_event_kwargs["team"] = home_team
    elif away_recipient_player:
        recipient_event_kwargs["player"] = away_recipient_player
        recipient_event_kwargs["team"] = away_team
    else:
        logger.warning(f"Unexpected recipient id: {raw_event['recipient_id']}")
        # raise DeserializationError(f"Unexpected recipient id: {raw_event['recipient_id']}")

    return recipient_event_kwargs


def _parse_duel(raw_event: Dict, action_id: int) -> (Dict, Dict):
    duel_qualifiers = []
    if action_id == AERIAL_DUEL:
        duel_qualifiers.append(DuelQualifier(value=DuelType.AERIAL))
    else:
        duel_qualifiers.append(DuelQualifier(value=DuelType.GROUND))
    if action_id == TACKLE:
        duel_qualifiers.append(DuelQualifier(value=DuelType.TACKLE))

    event_qualifiers = _get_event_qualifiers(raw_event)
    qualifiers = duel_qualifiers + event_qualifiers

    duel_won_event_kwargs = dict(
        result=DuelResult.WON,
        qualifiers=qualifiers,
    )
    duel_lost_event_kwargs = dict(
        result=DuelResult.LOST,
        qualifiers=qualifiers,
    )

    return duel_won_event_kwargs, duel_lost_event_kwargs


def _parse_substitution(
    raw_event: Dict, generic_event_kwargs: Dict, team: Team
) -> (Dict, Dict):
    substitution_generic_event_kwargs = generic_event_kwargs.copy()
    player_on = team.get_player_by_id(str(raw_event["creator_id"]))
    player_off = team.get_player_by_id(str(raw_event["recipient_id"]))
    substitution_generic_event_kwargs["player"] = player_off
    substitution_kwargs = dict(
        replacement_player=player_on, result=None, qualifiers=None
    )

    return substitution_kwargs, substitution_generic_event_kwargs


def _parse_interception(raw_event: Dict) -> Dict:
    qualifiers = _get_event_qualifiers(raw_event)
    result = InterceptionResult.SUCCESS

    return dict(
        result=result,
        qualifiers=qualifiers,
    )


def _get_pass_qualifiers(action_id: int) -> List[PassQualifier]:
    qualifiers = []
    if action_id in CROSS_IDS:
        qualifiers.append(PassQualifier(value=PassType.CROSS))
    if action_id == ASSIST:
        qualifiers.append(PassQualifier(value=PassType.ASSIST))

    return qualifiers


def _parse_pass(raw_event: Dict, action_id: int, team: Team) -> Dict:
    result = None
    receiver_coordinates = None
    receiver_player = None
    # We could check whether next event is offside to set PassResult.OFFSIDE
    if action_id in PASS_INACCURATE_IDS:
        result = PassResult.INCOMPLETE
    elif action_id in PASS_ACCURATE_IDS:
        result = PassResult.COMPLETE
        if (
            raw_event["relative_coord_x_destination"]
            and raw_event["relative_coord_y_destination"]
        ):
            receiver_coordinates = Point(
                x=raw_event["relative_coord_x_destination"],
                y=raw_event["relative_coord_y_destination"],
            )
        else:
            receiver_coordinates = None
        receiver_player = team.get_player_by_id(str(raw_event["recipient_id"]))

    event_qualifiers = _get_event_qualifiers(raw_event)
    pass_qualifiers = _get_pass_qualifiers(action_id)

    qualifiers = pass_qualifiers + event_qualifiers

    return dict(
        result=result,
        receiver_coordinates=receiver_coordinates,
        receiver_player=receiver_player,
        receive_timestamp=None,
        qualifiers=qualifiers,
    )


class SmrtStatsDeserializer(EventDataDeserializer[SmrtStatsInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.SMRTSTATS

    @staticmethod
    def create_team(team_info: Dict, ground: Ground) -> Team:
        team = Team(
            team_id=str(team_info["id"]), name=team_info["name"], ground=ground
        )

        return team

    @staticmethod
    def add_players(
        raw_events: Dict, home_team: Team, away_team: Team
    ) -> (Team, Team):
        def create_player(raw_event: Dict, team: Team) -> Player:
            starting = raw_event["second"] == 0.0
            position = POSITIONS[raw_event["action_id"]] if starting else None
            player_info = raw_event["creator"]
            first_name = player_info["name"]
            last_name = player_info["surname"]
            if first_name and last_name:
                full_name = player_info["name"] + " " + player_info["surname"]
            elif first_name:
                full_name = first_name
            elif last_name:
                full_name = last_name
            else:
                full_name = " "
            player = Player(
                player_id=str(player_info["id"]),
                team=team,
                jersey_no=player_info["number"],
                name=full_name,
                starting_position=position,
                starting=starting,
            )

            return player

        for idx, marker in enumerate(
            ["first_half_markers", "second_half_markers"]
        ):
            half_events = raw_events[marker]
            for event in half_events:
                action_id = event["action_id"]
                if action_id in POSITIONS:
                    if str(event["creator_team_id"]) == home_team.team_id:
                        player = create_player(event, home_team)
                        if player not in home_team.players:
                            home_team.players.append(player)
                    elif str(event["creator_team_id"]) == away_team.team_id:
                        player = create_player(event, away_team)
                        if player not in away_team.players:
                            away_team.players.append(player)
                    else:
                        raise DeserializationError(
                            f"Unexpected team id: {event['creator_team_id']}"
                        )
                elif action_id in FORMATIONS and idx == 0:
                    if str(event["creator_team_id"]) == home_team.team_id:
                        home_team.starting_formation = FORMATIONS[
                            event["action_id"]
                        ]
                    elif str(event["creator_team_id"]) == away_team.team_id:
                        away_team.starting_formation = FORMATIONS[
                            event["action_id"]
                        ]

        return home_team, away_team

    @staticmethod
    def create_periods(raw_events: Dict) -> List[Period]:
        periods = []
        for idx, marker in enumerate(
            ["first_half_markers", "second_half_markers"]
        ):
            half_events = raw_events[marker]
            start_timestamp = (
                timedelta(0) if not periods else periods[-1].end_timestamp
            )
            period = Period(
                id=idx + 1,
                start_timestamp=start_timestamp,
                end_timestamp=timedelta(seconds=(half_events[-1]["second"])),
            )
            periods.append(period)

        return periods

    def deserialize(self, inputs: SmrtStatsInputs) -> EventDataset:
        transformer = self.get_transformer(
            inputs.pitch_length, inputs.pitch_width
        )

        with performance_logging("load data", logger=logger):
            raw_data = json.load(inputs.raw_data)

        match_info = raw_data["match"]
        home_team = self.create_team(match_info["home_team"], Ground.HOME)
        away_team = self.create_team(match_info["away_team"], Ground.AWAY)
        home_team, away_team = self.add_players(raw_data, home_team, away_team)
        teams = {home_team.team_id: home_team, away_team.team_id: away_team}
        periods = self.create_periods(raw_data)
        score = Score(
            home=match_info["home_team_score"],
            away=match_info["away_team_score"],
        )
        possession_team = None

        events = []
        for period_events_title, period_id in zip(
            ["first_half_markers", "second_half_markers"], [1, 2]
        ):
            period_events = raw_data[period_events_title]
            for idx, raw_event in enumerate(period_events):
                action_id = raw_event["action_id"]
                action_title = raw_event["action"]["title"].lower()
                if (
                    action_id not in ACTION_IDS_TO_IGNORE
                    and raw_event["creator_team_id"]
                    and raw_event["creator_id"]
                ):
                    team = teams[str(raw_event["creator_team_id"])]
                    player = team.get_player_by_id(
                        str(raw_event["creator_id"])
                    )
                    period = next(
                        period for period in periods if period.id == period_id
                    )
                    if action_id in BALL_OWNING_IDS:
                        possession_team = team

                    if (
                        raw_event["relative_coord_x"]
                        and raw_event["relative_coord_y"]
                    ):
                        coordinates = Point(
                            x=raw_event["relative_coord_x"],
                            y=raw_event["relative_coord_y"],
                        )
                    else:
                        logger.debug(
                            f"Not setting coordinates for event with missing coordinates: {raw_event}"
                        )
                        coordinates = None
                    generic_event_kwargs = dict(
                        period=period,
                        timestamp=timedelta(seconds=raw_event["second"])
                        if period.id == 1
                        else timedelta(
                            seconds=(raw_event["second"] - 45 * 60)
                        ),
                        ball_owning_team=possession_team,
                        ball_state=None,
                        event_id=str(raw_event["id"]),
                        team=team,
                        player=player,
                        coordinates=coordinates,
                        raw_event=raw_event,
                    )

                    if action_id in PASS_IDS:
                        pass_event_args = _parse_pass(
                            raw_event, action_id, team
                        )
                        event = self.event_factory.build_pass(
                            **pass_event_args, **generic_event_kwargs
                        )
                    elif action_id in SHOT_IDS:
                        shot_event_kwargs = _parse_shot(raw_event, action_id)
                        event = self.event_factory.build_shot(
                            **shot_event_kwargs, **generic_event_kwargs
                        )
                    elif action_id in INTERCEPTION_IDS:
                        interception_kwargs = _parse_interception(raw_event)
                        event = self.event_factory.build_interception(
                            **interception_kwargs, **generic_event_kwargs
                        )
                    elif action_id in TAKE_ON_IDS:
                        take_on_kwargs = _parse_take_on(raw_event, action_id)
                        event = self.event_factory.build_take_on(
                            **take_on_kwargs, **generic_event_kwargs
                        )
                    elif action_id == CLEARANCE:
                        event = self.event_factory.build_clearance(
                            **dict(
                                qualifiers=_get_event_qualifiers(raw_event),
                                result=None,
                            ),
                            **generic_event_kwargs,
                        )
                    elif action_id == PICKING_UP:
                        event = self.event_factory.build_recovery(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )
                    elif action_id in FOUL_IDS:
                        event = self.event_factory.build_foul_committed(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )
                    elif action_id in CARD_IDS:
                        card_event_kwargs = _parse_card(raw_event, action_id)
                        event = self.event_factory.build_card(
                            **card_event_kwargs,
                            **generic_event_kwargs,
                        )
                    elif action_id in GOALKEEPER_IDS:
                        goalkeeper_kwargs = _parse_goalkeeper_events(
                            raw_event, action_id
                        )
                        event = self.event_factory.build_goalkeeper_event(
                            **goalkeeper_kwargs, **generic_event_kwargs
                        )
                    elif action_id == TACKLE:
                        (
                            duel_won_event_kwargs,
                            duel_lost_event_kwargs,
                        ) = _parse_duel(raw_event, action_id)
                        event = self.event_factory.build_duel(
                            **duel_won_event_kwargs, **generic_event_kwargs
                        )
                    elif action_id in TWO_PEOPLE_DUEL_IDS:
                        (
                            duel_won_event_kwargs,
                            duel_lost_event_kwargs,
                        ) = _parse_duel(raw_event, action_id)
                        duel_won_event = self.event_factory.build_duel(
                            **duel_won_event_kwargs, **generic_event_kwargs
                        )
                        recipient_generic_event_kwargs = (
                            _update_recipient_event_kwargs(
                                generic_event_kwargs,
                                raw_event,
                                home_team,
                                away_team,
                            )
                        )
                        duel_lost_event = self.event_factory.build_duel(
                            **duel_lost_event_kwargs,
                            **recipient_generic_event_kwargs,
                        )
                        if self.should_include_event(
                            duel_won_event
                        ) and self.should_include_event(duel_lost_event):
                            events.extend(
                                [
                                    transformer.transform_event(
                                        duel_won_event
                                    ),
                                    transformer.transform_event(
                                        duel_lost_event
                                    ),
                                ]
                            )
                        continue
                    elif action_id == SUBSTITUTION:
                        (
                            substitution_event_kwargs,
                            updated_generic_event_kwargs,
                        ) = _parse_substitution(
                            raw_event, generic_event_kwargs, team
                        )
                        event = self.event_factory.build_substitution(
                            **substitution_event_kwargs,
                            **updated_generic_event_kwargs,
                        )
                    else:
                        event = self.event_factory.build_generic(
                            **generic_event_kwargs,
                            result=None,
                            qualifiers=None,
                            event_name=action_title,
                        )

                    if self.should_include_event(event):
                        events.append(transformer.transform_event(event))

        metadata = Metadata(
            teams=[home_team, away_team],
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=score,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=None,
            provider=Provider.SMRTSTATS,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return EventDataset(
            metadata=metadata,
            records=events,
        )
