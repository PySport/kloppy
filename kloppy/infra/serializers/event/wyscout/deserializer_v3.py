import json
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    CardType,
    CarryResult,
    CounterAttackQualifier,
    DuelQualifier,
    DuelResult,
    DuelType,
    EventDataset,
    FormationType,
    GoalkeeperActionType,
    GoalkeeperQualifier,
    Ground,
    InterceptionResult,
    Metadata,
    Orientation,
    PassQualifier,
    PassResult,
    PassType,
    Period,
    Player,
    Point,
    PositionType,
    Provider,
    Qualifier,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    TakeOnResult,
    Team,
)
from kloppy.exceptions import DeserializationError
from kloppy.utils import performance_logging

from ..deserializer import EventDataDeserializer
from .deserializer_v2 import WyscoutInputs

logger = logging.getLogger(__name__)


INVALID_PLAYER = "0"

formations = {
    "4-4-2": FormationType.FOUR_FOUR_TWO,
    "4-4-1-1": FormationType.FOUR_FOUR_ONE_ONE,
    "4-3-2-1": FormationType.FOUR_THREE_TWO_ONE,
    "4-2-3-1": FormationType.FOUR_TWO_THREE_ONE,
    "4-1-4-1": FormationType.FOUR_ONE_FOUR_ONE,
    "4-1-3-2": FormationType.FOUR_ONE_THREE_TWO,
    "4-3-1-2": FormationType.FOUR_THREE_ONE_TWO,
    "4-3-3": FormationType.FOUR_THREE_THREE,
    "4-5-1": FormationType.FOUR_FIVE_ONE,
    "4-2-2-2": FormationType.FOUR_TWO_TWO_TWO,
    "4-2-1-3": FormationType.FOUR_TWO_ONE_THREE,
    "3-4-3": FormationType.THREE_FOUR_THREE,
    "3-4-1-2": FormationType.THREE_FOUR_ONE_TWO,
    "3-4-2-1": FormationType.THREE_FOUR_TWO_ONE,
    "3-5-2": FormationType.THREE_FIVE_TWO,
    "3-5-1-1": FormationType.THREE_FIVE_ONE_ONE,
    "5-3-2": FormationType.FIVE_THREE_TWO,
    "5-4-1": FormationType.FIVE_FOUR_ONE,
    "3-3-3-1": FormationType.THREE_THREE_THREE_ONE,
    "3-2-3-2": FormationType.THREE_TWO_THREE_TWO,
}

position_types_mapping: Dict[str, PositionType] = {
    "GK": PositionType.Goalkeeper,
    "LB": PositionType.LeftBack,
    "LWB": PositionType.LeftWingBack,
    "LB5": PositionType.LeftBack,
    "LCB": PositionType.LeftCenterBack,
    "LCB3": PositionType.LeftCenterBack,
    "CB": PositionType.CenterBack,
    "RCB": PositionType.RightCenterBack,
    "RCB3": PositionType.RightCenterBack,
    "RB": PositionType.RightBack,
    "RWB": PositionType.RightWingBack,
    "RB5": PositionType.RightBack,
    "LW": PositionType.LeftWing,
    "LAMF": PositionType.LeftAttackingMidfield,
    "LCMF3": PositionType.LeftCentralMidfield,
    "LCMF": PositionType.LeftCentralMidfield,
    "DMF": PositionType.DefensiveMidfield,
    "LDMF": PositionType.LeftDefensiveMidfield,
    "RDMF": PositionType.RightDefensiveMidfield,
    "RCMF3": PositionType.RightCentralMidfield,
    "RCMF": PositionType.RightCentralMidfield,
    "RAMF": PositionType.RightAttackingMidfield,
    "RW": PositionType.RightWing,
    "AMF": PositionType.AttackingMidfield,
    "LWF": PositionType.LeftForward,
    "CF": PositionType.Striker,
    "SS": PositionType.Striker,
    "RWF": PositionType.RightForward,
}


def _flip_point(point: Point) -> Point:
    return Point(x=100 - point.x, y=100 - point.y)


class ShotZoneResults(str, Enum):
    GOAL_BOTTOM_LEFT = "glb"
    GOAL_BOTTOM_RIGHT = "grb"
    GOAL_BOTTOM_CENTER = "gb"
    GOAL_CENTER_LEFT = "gl"
    GOAL_CENTER = "gc"
    GOAL_CENTER_RIGHT = "gr"
    GOAL_TOP_LEFT = "glt"
    GOAL_TOP_RIGHT = "grt"
    GOAL_TOP_CENTER = "gt"
    OUT_BOTTOM_RIGHT = "obr"
    OUT_BOTTOM_LEFT = "olb"
    OUT_RIGHT = "or"
    OUT_LEFT = "ol"
    OUT_LEFT_TOP = "olt"
    OUT_TOP = "ot"
    OUT_RIGHT_TOP = "ort"
    BLOCKED = "bc"


def _parse_team(raw_events, wyId: str, ground: Ground) -> Team:
    # Get the first formation description
    first_period_formation_info = raw_events["formations"][wyId]["1H"]
    first_formation_descr = next(iter(first_period_formation_info.values()))
    formation_str, formation_info = next(iter(first_formation_descr.items()))

    # Extract the formation and players' positions
    starting_formation = formations.get(formation_str)
    starting_players_positions = {
        player_id: position_types_mapping.get(
            player_info["position"].upper(), PositionType.Unknown
        )
        for player_descr in formation_info["players"]
        for player_id, player_info in player_descr.items()
    }

    team = Team(
        team_id=wyId,
        name=raw_events["teams"][wyId]["team"]["officialName"],
        ground=ground,
        starting_formation=starting_formation,
    )

    for player in raw_events["players"][wyId]:
        player_id = str(player["player"]["wyId"])
        starting_position = starting_players_positions.get(player_id)
        team.players.append(
            Player(
                player_id=player_id,
                team=team,
                jersey_no=None,
                first_name=player["player"]["firstName"],
                last_name=player["player"]["lastName"],
                starting=starting_position is not None,
                starting_position=starting_position,
            )
        )

    return team


def _create_shot_result_coordinates(raw_event: Dict) -> Optional[Point]:
    """Estimate the shot end location from the Wyscout tags.

    Wyscout does not provide end-coordinates of shots. Instead shots on goal
    are tagged with a zone. This function maps each of these zones to
    a coordinate. The zones and corresponding y-coordinate are depicted below.


        olt      | ot |      ort
     --------------------------------
          ||=================||
     -------------------------------
          || glt | gt | grt ||
     --------------------------------
      ol || gl | gc  | gr || or
     --------------------------------
      olb || glb  | gb | grb || orb

      40     45    50    55     60    (y-coordinate of zone)
        44.62               55.38     (y-coordiante of post)
    """
    if (
        raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_BOTTOM_CENTER
        or raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_CENTER
        or raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_TOP_CENTER
    ):
        return Point(100.0, 50.0)

    if (
        raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_BOTTOM_RIGHT
        or raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_CENTER_RIGHT
        or raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_TOP_RIGHT
    ):
        return Point(100.0, 55.0)

    if (
        raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_BOTTOM_LEFT
        or raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_CENTER_LEFT
        or raw_event["shot"]["goalZone"] == ShotZoneResults.GOAL_TOP_LEFT
    ):
        return Point(100.0, 45.0)

    if raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_TOP:
        return Point(100.0, 50.0)

    if (
        raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_RIGHT_TOP
        or raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_RIGHT
        or raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_BOTTOM_RIGHT
    ):
        return Point(100.0, 60.0)

    if (
        raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_LEFT_TOP
        or raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_LEFT
        or raw_event["shot"]["goalZone"] == ShotZoneResults.OUT_BOTTOM_LEFT
    ):
        return Point(100.0, 40.0)

    # If the shot is blocked, the start location is the best possible estimate
    # for the shot's end location
    if raw_event["shot"]["goalZone"] == ShotZoneResults.BLOCKED:
        return Point(
            x=float(raw_event["location"]["x"]),
            y=float(raw_event["location"]["y"]),
        )

    return None


def _generic_qualifiers(raw_event: Dict) -> List[Qualifier]:
    qualifiers: List[Qualifier] = []

    counter_attack_qualifier = CounterAttackQualifier(False)
    if raw_event["possession"]:
        if "counterattack" in raw_event["possession"]["types"]:
            counter_attack_qualifier = CounterAttackQualifier(True)
    qualifiers.append(counter_attack_qualifier)

    return qualifiers


def _parse_shot(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    if raw_event["shot"]["isGoal"] is True:
        result = ShotResult.GOAL
    elif raw_event["shot"]["onTarget"] is True:
        result = ShotResult.SAVED
    elif raw_event["shot"]["goalZone"] == "bc":
        result = ShotResult.BLOCKED
    else:
        result = ShotResult.OFF_TARGET

    if raw_event["shot"]["bodyPart"] == "head_or_other":
        qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))
    elif raw_event["shot"]["bodyPart"] == "left_foot":
        qualifiers.append(BodyPartQualifier(value=BodyPart.LEFT_FOOT))
    elif raw_event["shot"]["bodyPart"] == "right_foot":
        qualifiers.append(BodyPartQualifier(value=BodyPart.RIGHT_FOOT))

    return {
        "result": result,
        "result_coordinates": _create_shot_result_coordinates(raw_event),
        "qualifiers": qualifiers,
    }


def _check_secondary_event_types(
    raw_event, secondary_event_types_values: List[str]
) -> bool:
    return any(
        secondary_event_types in secondary_event_types_values
        for secondary_event_types in raw_event["type"]["secondary"]
    )


def _pass_qualifiers(raw_event) -> List[Qualifier]:
    qualifiers = _generic_qualifiers(raw_event)

    qualifier_mapping = {
        PassType.CROSS: ["cross", "cross_blocked"],
        PassType.HAND_PASS: ["hand_pass"],
        PassType.HEAD_PASS: ["head_pass"],
        PassType.SMART_PASS: ["smart_pass"],
        PassType.SHOT_ASSIST: ["shot_assist"],
        PassType.ASSIST: ["assist"],
    }

    for pass_type, secondary_event_types_values in qualifier_mapping.items():
        if _check_secondary_event_types(
            raw_event, secondary_event_types_values
        ):
            qualifiers.append(PassQualifier(pass_type))

    return qualifiers


def _parse_pass(raw_event: Dict, next_event: Dict, team: Team) -> Dict:
    pass_result = None
    receiver_player = None
    if len(raw_event["pass"]["endLocation"]) > 1:
        receiver_coordinates = Point(
            x=float(raw_event["pass"]["endLocation"]["x"]),
            y=float(raw_event["pass"]["endLocation"]["y"]),
        )
    else:
        receiver_coordinates = None

    if raw_event["pass"]["accurate"] is True:
        pass_result = PassResult.COMPLETE
        receiver_player = team.get_player_by_id(
            raw_event["pass"]["recipient"]["id"]
        )
    elif raw_event["pass"]["accurate"] is False:
        pass_result = PassResult.INCOMPLETE

    if raw_event["pass"].get("height") == "blocked":
        receiver_coordinates = None

    if next_event:
        if next_event["type"]["primary"] == "offside":
            pass_result = PassResult.OFFSIDE
        if next_event["type"]["primary"] == "game_interruption":
            if "ball_out" in next_event["type"]["secondary"]:
                pass_result = PassResult.OUT
        # Set end coordinates of blocked pass to start coordinates of next event if it is not a game interruption
        if raw_event["pass"].get("height") == "blocked":
            next_event_location = Point(
                x=float(next_event["location"]["x"]),
                y=float(next_event["location"]["y"]),
            )
            if team.team_id == str(next_event["team"]["id"]):
                receiver_coordinates = next_event_location
            else:
                receiver_coordinates = _flip_point(next_event_location)

    return {
        "result": pass_result,
        "qualifiers": _pass_qualifiers(raw_event),
        "receive_timestamp": None,
        "receiver_player": receiver_player,
        "receiver_coordinates": receiver_coordinates,
    }


def _parse_foul(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {
        "result": None,
        "qualifiers": qualifiers,
    }


def _parse_card(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    card_type = None
    if _check_secondary_event_types(raw_event, ["yellow_card"]):
        card_type = CardType.FIRST_YELLOW
    elif _check_secondary_event_types(raw_event, ["red_card"]):
        card_type = CardType.RED

    return {"result": None, "qualifiers": qualifiers, "card_type": card_type}


def _parse_recovery(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {
        "result": None,
        "qualifiers": qualifiers,
    }


def _parse_clearance(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {
        "result": None,
        "qualifiers": qualifiers,
    }


def _parse_interception(raw_event: Dict, next_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    result = InterceptionResult.SUCCESS

    if next_event is not None:
        is_game_interruption = (
            next_event["type"]["primary"] == "game_interruption"
        )
        is_ball_out = "ball_out" in next_event["type"]["secondary"]
        is_loss = "loss" in raw_event["type"]["secondary"]
        is_pass_loss = (
            "pass" in raw_event["type"]["secondary"]
            and raw_event["pass"]["accurate"] is False
        )
        is_possession_loss = (
            next_event["possession"] is not None
            and raw_event["team"]["id"]
            != next_event["possession"]["team"]["id"]
        )

        if is_game_interruption and is_ball_out:
            result = InterceptionResult.OUT
        elif is_loss or is_pass_loss or is_possession_loss:
            result = InterceptionResult.LOST

    return {
        "result": result,
        "qualifiers": qualifiers,
    }


def _parse_carry(raw_event: Dict, next_event: Dict, start_ts: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    carry_info = raw_event["carry"]
    end_coordinates = Point(
        x=float(carry_info["endLocation"]["x"]),
        y=float(carry_info["endLocation"]["y"]),
    )

    if next_event is not None:
        period_id = _parse_period_id(next_event["matchPeriod"])
        end_timestamp = _create_timestamp_timedelta(
            next_event, start_ts, period_id
        )
    else:
        period_id = _parse_period_id(raw_event["matchPeriod"])
        end_timestamp = _create_timestamp_timedelta(
            raw_event, start_ts, period_id
        )

    return {
        "result": CarryResult.COMPLETE,
        "qualifiers": qualifiers,
        "end_coordinates": end_coordinates,
        "end_timestamp": end_timestamp,
    }


def _parse_goalkeeper_save(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)

    goalkeeper_qualifiers = []
    if "save" in raw_event["type"]["secondary"]:
        goalkeeper_qualifiers.append(
            GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)
        )

    if "save_with_reflex" == "save_with_reflex":
        goalkeeper_qualifiers.append(
            GoalkeeperQualifier(value=GoalkeeperActionType.REFLEX)
        )
    qualifiers.extend(goalkeeper_qualifiers)

    return {"result": None, "qualifiers": qualifiers}


def _parse_ball_out(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {"result": None, "qualifiers": qualifiers}


def _parse_set_piece(raw_event: Dict, next_event: Dict, team: Team) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    result = {}

    # Pass set pieces
    if raw_event["type"]["primary"] == "goal_kick":
        qualifiers.append(SetPieceQualifier(SetPieceType.GOAL_KICK))
        result = _parse_pass(raw_event, next_event, team)
    elif raw_event["type"]["primary"] == "throw_in":
        qualifiers.append(SetPieceQualifier(SetPieceType.THROW_IN))
        qualifiers.append(PassQualifier(PassType.HAND_PASS))
        result = _parse_pass(raw_event, next_event, team)
    elif (
        raw_event["type"]["primary"] == "free_kick"
    ) and "free_kick_shot" not in raw_event["type"]["secondary"]:
        qualifiers.append(SetPieceQualifier(SetPieceType.FREE_KICK))
        result = _parse_pass(raw_event, next_event, team)
    elif (
        raw_event["type"]["primary"] == "corner"
    ) and "shot" not in raw_event["type"]["secondary"]:
        qualifiers.append(SetPieceQualifier(SetPieceType.CORNER_KICK))
        result = _parse_pass(raw_event, next_event, team)
    # Shot set pieces
    elif (
        raw_event["type"]["primary"] == "free_kick"
    ) and "free_kick_shot" in raw_event["type"]["secondary"]:
        qualifiers.append(SetPieceQualifier(SetPieceType.FREE_KICK))
        result = _parse_shot(raw_event)
    elif (raw_event["type"]["primary"] == "corner") and "shot" in raw_event[
        "type"
    ]["secondary"]:
        qualifiers.append(SetPieceQualifier(SetPieceType.CORNER_KICK))
        result = _parse_shot(raw_event)
    elif raw_event["type"]["primary"] == "penalty":
        qualifiers.append(SetPieceQualifier(SetPieceType.PENALTY))
        result = _parse_shot(raw_event)

    result["qualifiers"] = qualifiers
    return result


def _parse_take_on(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    result = None
    if "offensive_duel" in raw_event["type"]["secondary"]:
        if raw_event["groundDuel"]["keptPossession"]:
            result = TakeOnResult.COMPLETE
        else:
            result = TakeOnResult.INCOMPLETE
    elif "defensive_duel" in raw_event["type"]["secondary"]:
        if raw_event["groundDuel"]["recoveredPossession"]:
            result = TakeOnResult.COMPLETE
        else:
            result = TakeOnResult.INCOMPLETE
    elif "aerial_duel" in raw_event["type"]["secondary"]:
        if raw_event["aerialDuel"]["firstTouch"]:
            result = TakeOnResult.COMPLETE
        else:
            result = TakeOnResult.INCOMPLETE

    return {"result": result, "qualifiers": qualifiers}


def _parse_duel(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    duel_qualifiers = []
    secondary_types = raw_event["type"]["secondary"]

    if "ground_duel" in secondary_types:
        duel_qualifiers.append(DuelQualifier(value=DuelType.GROUND))
    elif "aerial_duel" in secondary_types:
        duel_qualifiers.extend(
            [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=DuelType.AERIAL),
            ]
        )
    else:
        if (
            "loose_ball_duel" in secondary_types
            and "sliding_tackle" in secondary_types
        ):
            duel_qualifiers.extend(
                [
                    DuelQualifier(value=DuelType.GROUND),
                    DuelQualifier(value=DuelType.LOOSE_BALL),
                    DuelQualifier(value=DuelType.SLIDING_TACKLE),
                ]
            )
        elif "loose_ball_duel" in secondary_types:
            duel_qualifiers.extend(
                [
                    DuelQualifier(value=DuelType.GROUND),
                    DuelQualifier(value=DuelType.LOOSE_BALL),
                ]
            )
        elif "sliding_tackle" in secondary_types:
            duel_qualifiers.extend(
                [
                    DuelQualifier(value=DuelType.GROUND),
                    DuelQualifier(value=DuelType.SLIDING_TACKLE),
                ]
            )

    qualifiers.extend(duel_qualifiers)

    if (
        "offensive_duel" in secondary_types
        and raw_event["groundDuel"]["keptPossession"]
    ):
        result = DuelResult.WON
    elif (
        "defensive_duel" in secondary_types
        and raw_event["groundDuel"]["recoveredPossession"]
    ):
        result = DuelResult.WON
    elif (
        "aerial_duel" in secondary_types
        and raw_event["aerialDuel"]["firstTouch"]
    ):
        result = DuelResult.WON
    else:
        result = DuelResult.LOST

    return {"result": result, "qualifiers": qualifiers}


def _create_timestamp_timedelta(
    raw_event: Dict, start_ts: Dict, period_id: int
) -> timedelta:
    time_delta = (
        timedelta(
            seconds=float(raw_event["second"] + raw_event["minute"] * 60)
        )
        - start_ts[period_id]
    )

    return time_delta


def get_home_away_team_formation(event, team):
    if team.ground == Ground.HOME:
        current_home_team_formation = formations[event["team"]["formation"]]
        current_away_team_formation = formations[
            event["opponentTeam"]["formation"]
        ]
    elif team.ground == Ground.AWAY:
        current_away_team_formation = formations[event["team"]["formation"]]
        current_home_team_formation = formations[
            event["opponentTeam"]["formation"]
        ]
    else:
        raise DeserializationError(f"Unknown team_id {team.team_id}")

    return current_home_team_formation, current_away_team_formation


def identify_synthetic_formation_change_event(
    raw_event, raw_next_event, teams, home_team, away_team
):
    current_event_team = teams[str(raw_event["team"]["id"])]
    next_event_team = teams[str(raw_next_event["team"]["id"])]
    event_formation_change_info = {}
    (
        current_home_team_formation,
        current_away_team_formation,
    ) = get_home_away_team_formation(raw_event, current_event_team)
    (
        next_home_team_formation,
        next_away_team_formation,
    ) = get_home_away_team_formation(raw_next_event, next_event_team)
    if next_home_team_formation != current_home_team_formation:
        event_formation_change_info[home_team] = {
            "formation_type": next_home_team_formation
        }

    if next_away_team_formation != current_away_team_formation:
        event_formation_change_info[away_team] = {
            "formation_type": next_away_team_formation
        }

    return event_formation_change_info


def _players_to_dict(players: List[Player]):
    return {player.player_id: player for player in players}


def _parse_period_id(raw_period: str) -> int:
    if "H" in raw_period:
        period_id = int(raw_period.replace("H", ""))
    elif "E" in raw_period:
        period_id = 2 + int(raw_period.replace("E", ""))
    elif raw_period == "P":
        period_id = 5
    else:
        raise DeserializationError(f"Unknown period {raw_period}")

    return period_id


class WyscoutDeserializerV3(EventDataDeserializer[WyscoutInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.WYSCOUT

    def deserialize(self, inputs: WyscoutInputs) -> EventDataset:
        transformer = self.get_transformer()

        with performance_logging("load data", logger=logger):
            raw_events = json.load(inputs.event_data)
            for event in raw_events["events"]:
                if "id" not in event:
                    event["id"] = event["type"]["primary"]

        periods = []
        # start timestamps are fixed
        start_ts = {
            1: timedelta(minutes=0),
            2: timedelta(minutes=45),
            3: timedelta(minutes=90),
            4: timedelta(minutes=105),
            5: timedelta(minutes=120),
        }

        with performance_logging("parse data", logger=logger):
            home_team_id, away_team_id = raw_events["teams"].keys()
            home_team = _parse_team(raw_events, home_team_id, Ground.HOME)
            away_team = _parse_team(raw_events, away_team_id, Ground.AWAY)
            teams = {home_team_id: home_team, away_team_id: away_team}
            players = dict(
                [
                    (wyId, _players_to_dict(team.players))
                    for wyId, team in teams.items()
                ]
            )
            date = raw_events["match"].get("dateutc")
            if date:
                date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            game_week = raw_events["match"].get("gameweek")
            if game_week:
                game_week = str(game_week)
            game_id = raw_events["events"][0].get("matchId")
            if game_id:
                game_id = str(game_id)
            home_coach = None
            away_coach = None
            coaches = raw_events.get("coaches")
            if coaches:
                if (
                    home_team_id in coaches
                    and "coach" in coaches[home_team_id]
                ):
                    home_coach = coaches[home_team_id]["coach"].get(
                        "shortName"
                    )
                if (
                    away_team_id in coaches
                    and "coach" in coaches[away_team_id]
                ):
                    away_coach = coaches[away_team_id]["coach"].get(
                        "shortName"
                    )

            events = []

            for idx, raw_event in enumerate(raw_events["events"]):
                next_event = None
                next_period_id = None
                if (idx + 1) < len(raw_events["events"]):
                    next_event = raw_events["events"][idx + 1]
                    next_period_id = _parse_period_id(
                        next_event["matchPeriod"]
                    )

                team_id = str(raw_event["team"]["id"])
                team = teams[team_id]
                player_id = str(raw_event["player"]["id"])
                period_id = _parse_period_id(raw_event["matchPeriod"])

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
                        end_timestamp=timedelta(
                            seconds=float(
                                raw_event["second"] + raw_event["minute"] * 60
                            )
                        ),
                    )

                ball_owning_team = None
                if raw_event["possession"]:
                    ball_owning_team = teams[
                        str(raw_event["possession"]["team"]["id"])
                    ]

                generic_event_args = {
                    "event_id": raw_event["id"],
                    "raw_event": raw_event,
                    "coordinates": (
                        Point(
                            x=float(raw_event["location"]["x"]),
                            y=float(raw_event["location"]["y"]),
                        )
                        if raw_event["location"]
                        else None
                    ),
                    "team": team,
                    "player": (
                        players[team_id][player_id]
                        if player_id != INVALID_PLAYER
                        else None
                    ),
                    "ball_owning_team": ball_owning_team,
                    "ball_state": None,
                    "period": periods[-1],
                    "timestamp": _create_timestamp_timedelta(
                        raw_event, start_ts, period_id
                    ),
                }

                primary_event_type = raw_event["type"]["primary"]
                secondary_event_types = raw_event["type"]["secondary"]
                if primary_event_type == "shot":
                    shot_event_args = _parse_shot(raw_event)
                    event = self.event_factory.build_shot(
                        **shot_event_args, **generic_event_args
                    )
                elif primary_event_type == "pass":
                    pass_event_args = _parse_pass(raw_event, next_event, team)
                    event = self.event_factory.build_pass(
                        **pass_event_args, **generic_event_args
                    )
                elif primary_event_type == "duel":
                    if "dribble" in secondary_event_types:
                        takeon_event_args = _parse_take_on(raw_event)
                        event = self.event_factory.build_take_on(
                            **takeon_event_args, **generic_event_args
                        )
                    else:
                        duel_event_args = _parse_duel(raw_event)
                        event = self.event_factory.build_duel(
                            **duel_event_args, **generic_event_args
                        )
                elif primary_event_type == "clearance":
                    clearance_event_args = _parse_clearance(raw_event)
                    event = self.event_factory.build_clearance(
                        **clearance_event_args, **generic_event_args
                    )
                elif primary_event_type == "interception":
                    interception_event_args = _parse_interception(
                        raw_event, next_event
                    )
                    event = self.event_factory.build_interception(
                        **interception_event_args, **generic_event_args
                    )
                elif (primary_event_type == "shot_against") & (
                    "save" in raw_event["type"]["secondary"]
                ):
                    goalkeeper_save_args = _parse_goalkeeper_save(raw_event)
                    event = self.event_factory.build_goalkeeper_event(
                        **goalkeeper_save_args, **generic_event_args
                    )
                elif (
                    (primary_event_type in ["throw_in", "goal_kick"])
                    or (
                        primary_event_type == "free_kick"
                        and "free_kick_shot" not in secondary_event_types
                    )
                    or (
                        primary_event_type == "corner"
                        and "shot" not in secondary_event_types
                    )
                ):
                    set_piece_event_args = _parse_set_piece(
                        raw_event, next_event, team
                    )
                    event = self.event_factory.build_pass(
                        **set_piece_event_args, **generic_event_args
                    )
                elif (
                    (primary_event_type == "penalty")
                    or (
                        primary_event_type == "free_kick"
                        and "free_kick_shot" in secondary_event_types
                    )
                    or (
                        primary_event_type == "corner"
                        and "shot" in secondary_event_types
                    )
                ):
                    set_piece_event_args = _parse_set_piece(
                        raw_event, next_event, team
                    )
                    event = self.event_factory.build_shot(
                        **set_piece_event_args, **generic_event_args
                    )
                elif primary_event_type == "infraction":
                    if "foul" in secondary_event_types:
                        foul_event_args = _parse_foul(raw_event)
                        event = self.event_factory.build_foul_committed(
                            **foul_event_args, **generic_event_args
                        )
                        # We already append event to events
                        # as we potentially have a card and foul event for one raw event
                        if event and self.should_include_event(event):
                            events.append(transformer.transform_event(event))
                        continue
                    if (
                        "yellow_card" in secondary_event_types
                        or "red_card" in secondary_event_types
                    ):
                        card_event_args = _parse_card(raw_event)
                        event = self.event_factory.build_card(
                            **card_event_args, **generic_event_args
                        )
                        if event and self.should_include_event(event):
                            events.append(transformer.transform_event(event))
                        continue
                elif "carry" in secondary_event_types:
                    carry_event_args = _parse_carry(
                        raw_event, next_event, start_ts
                    )
                    event = self.event_factory.build_carry(
                        **carry_event_args, **generic_event_args
                    )

                else:
                    event = self.event_factory.build_generic(
                        result=None,
                        qualifiers=_generic_qualifiers(raw_event),
                        event_name=raw_event["type"]["primary"],
                        **generic_event_args,
                    )

                if event and self.should_include_event(event):
                    events.append(transformer.transform_event(event))

                if next_event:
                    event_formation_change_info = (
                        identify_synthetic_formation_change_event(
                            raw_event, next_event, teams, home_team, away_team
                        )
                    )
                    for (
                        formation_change_team,
                        formation_change_event_kwargs,
                    ) in event_formation_change_info.items():
                        generic_event_args.update(
                            {
                                "event_id": f"synthetic-{raw_event['id']}",
                                "raw_event": None,
                                "coordinates": None,
                                "player": None,
                                "team": formation_change_team,
                            }
                        )
                        event = self.event_factory.build_formation_change(
                            result=None,
                            qualifiers=None,
                            **formation_change_event_kwargs,
                            **generic_event_args,
                        )
                        if event and self.should_include_event(event):
                            events.append(transformer.transform_event(event))

        metadata = Metadata(
            teams=[home_team, away_team],
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            score=None,
            frame_rate=None,
            orientation=Orientation.ACTION_EXECUTING_TEAM,
            flags=None,
            provider=Provider.WYSCOUT,
            coordinate_system=transformer.get_to_coordinate_system(),
            date=date,
            game_week=game_week,
            game_id=game_id,
            home_coach=home_coach,
            away_coach=away_coach,
        )

        return EventDataset(metadata=metadata, records=events)
