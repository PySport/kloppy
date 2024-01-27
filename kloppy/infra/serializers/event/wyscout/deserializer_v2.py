import json
import logging
from dataclasses import replace
from datetime import timedelta
from typing import Dict, List, Tuple, NamedTuple, IO, Optional

from kloppy.domain import (
    BodyPart,
    BodyPartQualifier,
    CardQualifier,
    CardType,
    CounterAttackQualifier,
    DuelResult,
    DuelQualifier,
    DuelType,
    EventDataset,
    EventType,
    GoalkeeperQualifier,
    GoalkeeperActionType,
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
    Provider,
    Qualifier,
    SetPieceQualifier,
    SetPieceType,
    ShotResult,
    Team,
)
from kloppy.utils import performance_logging

from . import wyscout_events, wyscout_tags
from ..deserializer import EventDataDeserializer

logger = logging.getLogger(__name__)


INVALID_PLAYER = "0"


def _parse_team(raw_events, wyId: str, ground: Ground) -> Team:
    team = Team(
        team_id=wyId,
        name=raw_events["teams"][wyId]["team"]["officialName"],
        ground=ground,
    )
    team.players = [
        Player(
            player_id=str(player["player"]["wyId"]),
            team=team,
            jersey_no=None,
            first_name=player["player"]["firstName"],
            last_name=player["player"]["lastName"],
        )
        for player in raw_events["players"][wyId]
    ]
    return team


def _has_tag(raw_event, tag_id) -> bool:
    for tag in raw_event["tags"]:
        if tag["id"] == tag_id:
            return True
    return False


def _generic_qualifiers(raw_event: Dict) -> List[Qualifier]:
    qualifiers: List[Qualifier] = []

    if _has_tag(raw_event, wyscout_tags.COUNTER_ATTACK):
        qualifiers.append(CounterAttackQualifier(True))
    else:
        qualifiers.append(CounterAttackQualifier(False))

    return qualifiers


def _bodypart_qualifiers(raw_event: Dict) -> List[Qualifier]:
    qualifiers = []
    if _has_tag(raw_event, wyscout_tags.LEFT_FOOT):
        qualifiers.append(BodyPartQualifier(BodyPart.LEFT_FOOT))
    elif _has_tag(raw_event, wyscout_tags.RIGHT_FOOT):
        qualifiers.append(BodyPartQualifier(BodyPart.RIGHT_FOOT))
    elif _has_tag(raw_event, wyscout_tags.HEAD_BODY):
        qualifiers.append(BodyPartQualifier(BodyPart.HEAD_OTHER))
    return qualifiers


def _create_shot_result_coordinates(raw_event: Dict) -> Optional[Point]:
    """Estimate the shot end location from the Wyscout tags.

    Wyscout does not provide end-coordinates of shots. Instead shots on goal
    are tagged with a zone. This function maps each of these zones to
    a coordinate. The zones and corresponding y-coordinate are depicted below.


        ohl      | ohc |      ohr
     --------------------------------
          ||=================||
     -------------------------------
          || ghl | ghc | ghr ||
     --------------------------------
      ocl || gcl | gc  | gcr || ocr
     --------------------------------
      oll || gll | glc | glr || olr

      40     45    50    55     60    (y-coordinate of zone)
        44.62               55.38     (y-coordiante of post)
    """
    if (
        _has_tag(raw_event, wyscout_tags.GOAL_LOW_CENTER)
        or _has_tag(raw_event, wyscout_tags.GOAL_CENTER)
        or _has_tag(raw_event, wyscout_tags.GOAL_HIGH_CENTER)
    ):
        return Point(100.0, 50.0)
    if (
        _has_tag(raw_event, wyscout_tags.GOAL_LOW_RIGHT)
        or _has_tag(raw_event, wyscout_tags.GOAL_CENTER_RIGHT)
        or _has_tag(raw_event, wyscout_tags.GOAL_HIGH_RIGHT)
    ):
        return Point(100.0, 55.0)
    if (
        _has_tag(raw_event, wyscout_tags.GOAL_LOW_LEFT)
        or _has_tag(raw_event, wyscout_tags.GOAL_CENTER_LEFT)
        or _has_tag(raw_event, wyscout_tags.GOAL_HIGH_LEFT)
    ):
        return Point(100.0, 45.0)
    if _has_tag(raw_event, wyscout_tags.OUT_HIGH_CENTER) or _has_tag(
        raw_event, wyscout_tags.POST_HIGH_CENTER
    ):
        return Point(100.0, 50.0)
    if (
        _has_tag(raw_event, wyscout_tags.OUT_LOW_RIGHT)
        or _has_tag(raw_event, wyscout_tags.OUT_CENTER_RIGHT)
        or _has_tag(raw_event, wyscout_tags.OUT_HIGH_RIGHT)
    ):
        return Point(100.0, 60.0)
    if (
        _has_tag(raw_event, wyscout_tags.OUT_LOW_LEFT)
        or _has_tag(raw_event, wyscout_tags.OUT_CENTER_LEFT)
        or _has_tag(raw_event, wyscout_tags.OUT_HIGH_LEFT)
    ):
        return Point(100.0, 40.0)
    if (
        _has_tag(raw_event, wyscout_tags.POST_LOW_LEFT)
        or _has_tag(raw_event, wyscout_tags.POST_CENTER_LEFT)
        or _has_tag(raw_event, wyscout_tags.POST_HIGH_LEFT)
    ):
        return Point(100.0, 55.38)
    if (
        _has_tag(raw_event, wyscout_tags.POST_LOW_RIGHT)
        or _has_tag(raw_event, wyscout_tags.POST_CENTER_RIGHT)
        or _has_tag(raw_event, wyscout_tags.POST_HIGH_RIGHT)
    ):
        return Point(100.0, 44.62)
    if _has_tag(raw_event, wyscout_tags.BLOCKED):
        return Point(
            x=float(raw_event["positions"][0]["x"]),
            y=float(raw_event["positions"][0]["y"]),
        )
    return None


def _parse_shot(raw_event: Dict, next_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    qualifiers.extend(_bodypart_qualifiers(raw_event))

    result = None
    if _has_tag(raw_event, 101):
        result = ShotResult.GOAL
    elif _has_tag(raw_event, 2101):
        result = ShotResult.BLOCKED
    elif any((_has_tag(raw_event, tag) for tag in wyscout_tags.SHOT_POST)):
        result = ShotResult.POST
    elif any(
        (_has_tag(raw_event, tag) for tag in wyscout_tags.SHOT_OFF_TARGET)
    ):
        result = ShotResult.OFF_TARGET
    elif any((_has_tag(raw_event, tag) for tag in wyscout_tags.SHOT_ON_GOAL)):
        result = ShotResult.SAVED

    if next_event["eventId"] == wyscout_events.SAVE.EVENT:
        if next_event["subEventId"] == wyscout_events.SAVE.REFLEXES:
            qualifiers.append(GoalkeeperQualifier(GoalkeeperActionType.REFLEX))
        if next_event["subEventId"] == wyscout_events.SAVE.SAVE_ATTEMPT:
            qualifiers.append(
                GoalkeeperQualifier(GoalkeeperActionType.SAVE_ATTEMPT)
            )

    return {
        "result": result,
        "result_coordinates": _create_shot_result_coordinates(raw_event),
        "qualifiers": qualifiers,
    }


def _pass_qualifiers(raw_event) -> List[Qualifier]:
    qualifiers = _generic_qualifiers(raw_event)

    if raw_event["subEventId"] == wyscout_events.PASS.CROSS:
        qualifiers.append(PassQualifier(PassType.CROSS))
    elif raw_event["subEventId"] == wyscout_events.PASS.HAND:
        qualifiers.append(PassQualifier(PassType.HAND_PASS))
        qualifiers.append(BodyPartQualifier(BodyPart.KEEPER_ARM))
    elif raw_event["subEventId"] == wyscout_events.PASS.HEAD:
        qualifiers.append(PassQualifier(PassType.HEAD_PASS))
        qualifiers.append(BodyPartQualifier(BodyPart.HEAD))
    elif raw_event["subEventId"] == wyscout_events.PASS.HIGH:
        qualifiers.append(PassQualifier(PassType.HIGH_PASS))
    elif raw_event["subEventId"] == wyscout_events.PASS.LAUNCH:
        qualifiers.append(PassQualifier(PassType.LAUNCH))
    elif raw_event["subEventId"] == wyscout_events.PASS.SIMPLE:
        qualifiers.append(PassQualifier(PassType.SIMPLE_PASS))
    elif raw_event["subEventId"] == wyscout_events.PASS.SMART:
        qualifiers.append(PassQualifier(PassType.SMART_PASS))

    # If the subevent type did not define the bodypart, we infer it from the tags
    if not any(isinstance(q, BodyPartQualifier) for q in qualifiers):
        qualifiers.extend(_bodypart_qualifiers(raw_event))

    if _has_tag(raw_event, wyscout_tags.HIGH):
        qualifiers.append(PassQualifier(PassType.HIGH_PASS))
    if _has_tag(raw_event, wyscout_tags.THROUGH):
        qualifiers.append(PassQualifier(PassType.THROUGH_BALL))
    if _has_tag(raw_event, wyscout_tags.ASSIST):
        qualifiers.append(PassQualifier(PassType.ASSIST))

    return qualifiers


def _parse_pass(raw_event: Dict, next_event: Dict) -> Dict:
    pass_result = None
    if _has_tag(raw_event, wyscout_tags.ACCURATE):
        pass_result = PassResult.COMPLETE
    elif _has_tag(raw_event, wyscout_tags.NOT_ACCURATE):
        pass_result = PassResult.INCOMPLETE

    receiver_coordinates = None
    if _has_tag(raw_event, wyscout_tags.BLOCKED):
        # blocked passes do not have end coordinates; the start coordinates
        # are used instead
        receiver_coordinates = Point(
            x=float(raw_event["positions"][0]["x"]),
            y=float(raw_event["positions"][0]["y"]),
        )
    elif len(raw_event["positions"]) > 1:
        receiver_coordinates = Point(
            x=float(raw_event["positions"][1]["x"]),
            y=float(raw_event["positions"][1]["y"]),
        )

    if next_event:
        if next_event["eventId"] == wyscout_events.OFFSIDE.EVENT:
            pass_result = PassResult.OFFSIDE
        if next_event["eventId"] == wyscout_events.INTERRUPTION.EVENT:
            if (
                next_event["subEventId"]
                == wyscout_events.INTERRUPTION.BALL_OUT
            ):
                pass_result = PassResult.OUT

    return {
        "result": pass_result,
        "qualifiers": _pass_qualifiers(raw_event),
        "receive_timestamp": None,
        "receiver_player": None,
        "receiver_coordinates": receiver_coordinates,
    }


def _parse_clearance(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {"result": None, "qualifiers": qualifiers}


def _parse_goalkeeper_save(raw_event) -> List[Qualifier]:
    qualifiers = _generic_qualifiers(raw_event)
    goalkeeper_qualifiers = []
    if not _has_tag(raw_event, wyscout_tags.GOAL):
        goalkeeper_qualifiers.append(
            GoalkeeperQualifier(value=GoalkeeperActionType.SAVE)
        )
    else:
        goalkeeper_qualifiers.append(
            GoalkeeperQualifier(value=GoalkeeperActionType.SAVE_ATTEMPT)
        )
    if raw_event["subEventId"] == wyscout_events.SAVE.REFLEXES:
        goalkeeper_qualifiers.append(
            GoalkeeperQualifier(value=GoalkeeperActionType.REFLEX)
        )
    qualifiers.extend(goalkeeper_qualifiers)
    return {
        "result": None,
        "qualifiers": qualifiers,
        # start coordinates are stored as inverted end coordinates
        "coordinates": Point(
            x=100.0 - float(raw_event["positions"][1]["x"]),
            y=100.0 - float(raw_event["positions"][1]["y"]),
        ),
    }


def _parse_foul(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)

    if _has_tag(raw_event, wyscout_tags.RED_CARD):
        qualifiers.append(CardQualifier(value=CardType.RED))
    elif _has_tag(raw_event, wyscout_tags.YELLOW_CARD):
        qualifiers.append(CardQualifier(value=CardType.FIRST_YELLOW))
    elif _has_tag(raw_event, wyscout_tags.SECOND_YELLOW_CARD):
        qualifiers.append(CardQualifier(value=CardType.SECOND_YELLOW))

    return {
        "result": None,
        "qualifiers": qualifiers,
    }


def _parse_card(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    card_type = None
    if _has_tag(raw_event, wyscout_tags.RED_CARD):
        card_type = CardType.RED
    elif _has_tag(raw_event, wyscout_tags.YELLOW_CARD):
        card_type = CardType.FIRST_YELLOW
    elif _has_tag(raw_event, wyscout_tags.SECOND_YELLOW_CARD):
        card_type = CardType.SECOND_YELLOW

    return {"result": None, "qualifiers": qualifiers, "card_type": card_type}


def _parse_recovery(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {
        "result": None,
        "qualifiers": qualifiers,
    }


def _parse_ball_out(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    return {"result": None, "qualifiers": qualifiers}


def _parse_set_piece(raw_event: Dict, next_event: Dict) -> Dict:
    result = {}
    if raw_event["subEventId"] in wyscout_events.FREE_KICK.PASS_TYPES:
        result = _parse_pass(raw_event, next_event)
        if raw_event["subEventId"] == wyscout_events.FREE_KICK.GOAL_KICK:
            result["qualifiers"].append(
                SetPieceQualifier(SetPieceType.GOAL_KICK)
            )
        elif raw_event["subEventId"] == wyscout_events.FREE_KICK.THROW_IN:
            result["qualifiers"].append(
                SetPieceQualifier(SetPieceType.THROW_IN)
            )
            result["qualifiers"].append(PassQualifier(PassType.HAND_PASS))
        elif raw_event["subEventId"] in [
            wyscout_events.FREE_KICK.FREE_KICK,
            wyscout_events.FREE_KICK.FREE_KICK_CROSS,
        ]:
            result["qualifiers"].append(
                SetPieceQualifier(SetPieceType.FREE_KICK)
            )
        elif raw_event["subEventId"] == wyscout_events.FREE_KICK.CORNER:
            result["qualifiers"].append(
                SetPieceQualifier(SetPieceType.CORNER_KICK)
            )
    elif raw_event["subEventId"] in wyscout_events.FREE_KICK.SHOT_TYPES:
        result = _parse_shot(raw_event, next_event)
        if raw_event["subEventId"] == wyscout_events.FREE_KICK.FREE_KICK_SHOT:
            result["qualifiers"].append(
                SetPieceQualifier(SetPieceType.FREE_KICK)
            )
        elif raw_event["subEventId"] == wyscout_events.FREE_KICK.PENALTY:
            result["qualifiers"].append(
                SetPieceQualifier(SetPieceType.PENALTY)
            )
    else:
        result["qualifiers"] = _generic_qualifiers(raw_event)
    return result


def _parse_interception(raw_event: Dict, next_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    result = InterceptionResult.SUCCESS
    ball_owning_events = (
        wyscout_events.PASS.EVENT,
        wyscout_events.SHOT.EVENT,
    )

    if next_event is not None:
        if next_event["eventId"] == wyscout_events.INTERRUPTION.EVENT:
            if (
                next_event["subEventId"]
                == wyscout_events.INTERRUPTION.BALL_OUT
            ):
                result = InterceptionResult.OUT
        elif raw_event["eventId"] == wyscout_events.PASS.EVENT:
            result = (
                InterceptionResult.LOST
                if _has_tag(raw_event, wyscout_tags.NOT_ACCURATE) is True
                else InterceptionResult.SUCCESS
            )
        # check whether team keeps ball possession
        elif next_event["eventId"] in ball_owning_events:
            if raw_event["teamId"] != next_event["teamId"]:
                result = InterceptionResult.LOST

    return {
        "result": result,
        "qualifiers": qualifiers,
    }


def _parse_duel(raw_event: Dict) -> Dict:
    qualifiers = _generic_qualifiers(raw_event)
    duel_qualifiers = []

    sub_event_id = raw_event["subEventId"]

    if sub_event_id == wyscout_events.DUEL.AERIAL:
        duel_qualifiers.extend(
            [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=DuelType.AERIAL),
            ]
        )
    elif sub_event_id in [
        wyscout_events.DUEL.GROUND_ATTACKING,
        wyscout_events.DUEL.GROUND_DEFENDING,
    ]:
        duel_qualifiers.extend([DuelQualifier(value=DuelType.GROUND)])
    elif sub_event_id == wyscout_events.DUEL.GROUND_LOOSE_BALL:
        duel_qualifiers.extend(
            [
                DuelQualifier(value=DuelType.LOOSE_BALL),
                DuelQualifier(value=DuelType.GROUND),
            ]
        )

    if _has_tag(raw_event, wyscout_tags.SLIDING_TACKLE):
        duel_qualifiers.extend([DuelQualifier(value=DuelType.SLIDING_TACKLE)])

    qualifiers.extend(duel_qualifiers)

    result = None
    if _has_tag(raw_event, wyscout_tags.WON):
        result = DuelResult.WON
    elif _has_tag(raw_event, wyscout_tags.LOST):
        result = DuelResult.LOST
    elif _has_tag(raw_event, wyscout_tags.NEUTRAL):
        result = DuelResult.NEUTRAL

    return {"result": result, "qualifiers": qualifiers}


def _players_to_dict(players: List[Player]):
    return {player.player_id: player for player in players}


class WyscoutInputs(NamedTuple):
    event_data: IO[bytes]


class WyscoutDeserializerV2(EventDataDeserializer[WyscoutInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.WYSCOUT

    def deserialize(self, inputs: WyscoutInputs) -> EventDataset:
        transformer = self.get_transformer(length=100, width=100)

        with performance_logging("load data", logger=logger):
            raw_events = json.load(inputs.event_data)
            for event in raw_events["events"]:
                if "eventId" not in event:
                    event["eventId"] = event["eventName"]
                if "subEventId" not in event:
                    event["subEventId"] = event.get("subEventName")

        periods = []

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

            events = []

            for idx, raw_event in enumerate(raw_events["events"]):
                next_event = None
                next_period_id = None
                if (idx + 1) < len(raw_events["events"]):
                    next_event = raw_events["events"][idx + 1]
                    next_period_id = int(
                        next_event["matchPeriod"].replace("H", "")
                    )

                team_id = str(raw_event["teamId"])
                player_id = str(raw_event["playerId"])
                period_id = int(raw_event["matchPeriod"].replace("H", ""))

                if len(periods) == 0 or periods[-1].id != period_id:
                    periods.append(
                        Period(
                            id=period_id,
                            start_timestamp=timedelta(seconds=0)
                            if len(periods) == 0
                            else periods[-1].end_timestamp,
                            end_timestamp=None,
                        )
                    )
                if next_period_id != period_id:
                    periods[-1] = replace(
                        periods[-1],
                        end_timestamp=periods[-1].start_timestamp
                        + timedelta(seconds=raw_event["eventSec"]),
                    )

                generic_event_args = {
                    "event_id": str(raw_event["id"]),
                    "raw_event": raw_event,
                    "coordinates": Point(
                        x=float(raw_event["positions"][0]["x"]),
                        y=float(raw_event["positions"][0]["y"]),
                    ),
                    "team": teams[team_id],
                    "player": players[team_id][player_id]
                    if player_id != INVALID_PLAYER
                    else None,
                    "ball_owning_team": None,
                    "ball_state": None,
                    "period": periods[-1],
                    "timestamp": timedelta(seconds=raw_event["eventSec"]),
                }

                new_events = []
                if raw_event["eventId"] == wyscout_events.SHOT.EVENT:
                    shot_event_args = _parse_shot(raw_event, next_event)
                    shot_event = self.event_factory.build_shot(
                        **shot_event_args, **generic_event_args
                    )
                    new_events.append(shot_event)
                elif raw_event["eventId"] == wyscout_events.PASS.EVENT:
                    pass_event_args = _parse_pass(raw_event, next_event)
                    pass_event = self.event_factory.build_pass(
                        **pass_event_args, **generic_event_args
                    )
                    new_events.append(pass_event)
                elif raw_event["eventId"] == wyscout_events.FOUL.EVENT:
                    foul_event_args = _parse_foul(raw_event)
                    foul_event = self.event_factory.build_foul_committed(
                        **foul_event_args, **generic_event_args
                    )
                    new_events.append(foul_event)
                    if any(
                        (_has_tag(raw_event, tag) for tag in wyscout_tags.CARD)
                    ):
                        card_event_args = _parse_card(raw_event)
                        card_event_id = (
                            f"card-{generic_event_args['event_id']}"
                        )
                        card_event = self.event_factory.build_card(
                            **card_event_args,
                            **{
                                **generic_event_args,
                                "event_id": card_event_id,
                            },
                        )
                        new_events.append(card_event)
                elif raw_event["eventId"] == wyscout_events.INTERRUPTION.EVENT:
                    ball_out_event_args = _parse_ball_out(raw_event)
                    ball_out_event = self.event_factory.build_ball_out(
                        **ball_out_event_args, **generic_event_args
                    )
                    new_events.append(ball_out_event)
                elif raw_event["eventId"] == wyscout_events.SAVE.EVENT:
                    goalkeeper_save_args = _parse_goalkeeper_save(raw_event)
                    goalkeeper_save_event = (
                        self.event_factory.build_goalkeeper_event(
                            **{**goalkeeper_save_args, **generic_event_args}
                        )
                    )
                    new_events.append(goalkeeper_save_event)
                elif raw_event["eventId"] == wyscout_events.FREE_KICK.EVENT:
                    set_piece_event_args = _parse_set_piece(
                        raw_event, next_event
                    )
                    if (
                        raw_event["subEventId"]
                        in wyscout_events.FREE_KICK.PASS_TYPES
                    ):
                        fk_pass_event = self.event_factory.build_pass(
                            **set_piece_event_args, **generic_event_args
                        )
                        new_events.append(fk_pass_event)
                    elif (
                        raw_event["subEventId"]
                        in wyscout_events.FREE_KICK.SHOT_TYPES
                    ):
                        fk_shot_event = self.event_factory.build_shot(
                            **set_piece_event_args, **generic_event_args
                        )
                        new_events.append(fk_shot_event)

                elif (
                    raw_event["eventId"] == wyscout_events.OTHERS_ON_BALL.EVENT
                ):
                    if (
                        raw_event["subEventId"]
                        == wyscout_events.OTHERS_ON_BALL.CLEARANCE
                    ):
                        clearance_event_args = _parse_clearance(raw_event)
                        clearance_event = self.event_factory.build_clearance(
                            **clearance_event_args,
                            **generic_event_args,
                        )
                        new_events.append(clearance_event)
                    elif (
                        raw_event["subEventId"]
                        == wyscout_events.OTHERS_ON_BALL.TOUCH
                    ) & (_has_tag(raw_event, wyscout_tags.MISSED_BALL)):
                        miscontrol_event_args = {
                            "result": None,
                            "qualifiers": _generic_qualifiers(raw_event),
                        }
                        miscontrol_event = self.event_factory.build_miscontrol(
                            **miscontrol_event_args,
                            **generic_event_args,
                        )
                        new_events.append(miscontrol_event)
                    else:
                        recovery_event_args = _parse_recovery(raw_event)
                        recovery_event = self.event_factory.build_recovery(
                            **recovery_event_args, **generic_event_args
                        )
                        new_events.append(recovery_event)
                elif raw_event["eventId"] == wyscout_events.DUEL.EVENT:
                    duel_event_args = _parse_duel(raw_event)
                    duel_event = self.event_factory.build_duel(
                        **duel_event_args, **generic_event_args
                    )
                    new_events.append(duel_event)
                elif raw_event["eventId"] not in [
                    wyscout_events.SAVE.EVENT,
                    wyscout_events.OFFSIDE.EVENT,
                ]:
                    # The events SAVE and OFFSIDE are already merged with PASS and SHOT events
                    qualifiers = _generic_qualifiers(raw_event)
                    generic_event = self.event_factory.build_generic(
                        result=None,
                        qualifiers=qualifiers,
                        **generic_event_args,
                    )
                    new_events.append(generic_event)

                # Wyscout v2 does not have a separate event type for
                # interceptions. Interceptions are recorded by adding a tag to
                # the next pass, touch or duel. Therefore, we convert events
                # with this tag to an interception.
                if _has_tag(raw_event, wyscout_tags.INTERCEPTION):
                    interception_event_args = _parse_interception(
                        raw_event, next_event
                    )

                    for i, new_event in enumerate(list(new_events)):
                        if new_event.event_type == EventType.DUEL:
                            # when DuelEvent is interception, we need to
                            # overwrite this and the previous DuelEvent
                            events = events[:-1]
                            new_events[
                                i
                            ] = self.event_factory.build_interception(
                                **interception_event_args,
                                **generic_event_args,
                            )
                        elif new_event.event_type in [
                            EventType.RECOVERY,
                            EventType.MISCONTROL,
                        ]:
                            # replace touch events
                            new_events[
                                i
                            ] = self.event_factory.build_interception(
                                **interception_event_args,
                                **generic_event_args,
                            )
                        elif new_event.event_type in [
                            EventType.PASS,
                            EventType.CLEARANCE,
                        ]:
                            # insert an interception event before interception passes
                            generic_event_args[
                                "event_id"
                            ] = f"interception-{generic_event_args['event_id']}"
                            interception_event = (
                                self.event_factory.build_interception(
                                    **interception_event_args,
                                    **generic_event_args,
                                )
                            )
                            new_events.insert(i, interception_event)

                for new_event in new_events:
                    if self.should_include_event(new_event):
                        events.append(transformer.transform_event(new_event))

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
        )

        return EventDataset(metadata=metadata, records=events)
