import json
import logging
from typing import Dict, List, Tuple

from kloppy.domain import (
    BallOutEvent,
    BodyPart,
    BodyPartQualifier,
    CardEvent,
    CardType,
    EventDataset,
    FoulCommittedEvent,
    GoalkeeperAction,
    GoalkeeperActionQualifier,
    Ground,
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
)
from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.utils import Readable, performance_logging

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


def _has_tag(raw_event, tag_id) -> bool:
    for tag in raw_event["tags"]:
        if tag["id"] == tag_id:
            return True
    return False


def _parse_shot(raw_event: Dict, next_event: Dict) -> Dict:
    result = None
    qualifiers = []
    if _has_tag(raw_event, 101):
        result = ShotResult.GOAL
    elif _has_tag(raw_event, 2101):
        result = ShotResult.BLOCKED
    elif any((_has_tag(raw_event, t) for t in range(1217, 1224))):
        result = ShotResult.POST
    elif any((_has_tag(raw_event, t) for t in range(1210, 1217))):
        result = ShotResult.OFF_TARGET
    elif any((_has_tag(raw_event, t) for t in range(1201, 1210))):
        result = ShotResult.SAVED

    if next_event["eventName"] == 9 and next_event["subEventName"] == 90:
        qualifiers.append(GoalkeeperActionQualifier(GoalkeeperAction.REFLEX))
    elif next_event["eventName"] == 9 and next_event["subEventName"] == 91:
        qualifiers.append(
            GoalkeeperActionQualifier(GoalkeeperAction.SAVE_ATTEMPT)
        )

    return {
        "result": result,
        "result_coordinates": Point(**raw_event["positions"][1]),
        "qualifiers": qualifiers,
    }


def _pass_qualifiers(raw_event) -> List[Qualifier]:
    qualifiers: List[Qualifier] = []

    if raw_event["subEventName"] == 80:
        qualifiers.append(PassQualifier(PassType.CROSS))
    elif raw_event["subEventName"] == 81:
        qualifiers.append(PassQualifier(PassType.HAND_PASS))
    elif raw_event["subEventName"] == 82:
        qualifiers.append(PassQualifier(PassType.HEAD_PASS))
    elif raw_event["subEventName"] == 83:
        qualifiers.append(PassQualifier(PassType.HIGH_PASS))
    elif raw_event["subEventName"] == 84:
        qualifiers.append(PassQualifier(PassType.LAUNCH))
    elif raw_event["subEventName"] == 85:
        qualifiers.append(PassQualifier(PassType.SIMPLE_PASS))
    elif raw_event["subEventName"] == 86:
        qualifiers.append(PassQualifier(PassType.SMART_PASS))

    if _has_tag(raw_event, 401):
        qualifiers.append(BodyPartQualifier(BodyPart.LEFT_FOOT))
    elif _has_tag(raw_event, 402):
        qualifiers.append(BodyPartQualifier(BodyPart.RIGHT_FOOT))

    return qualifiers


def _parse_pass(raw_event: Dict, next_event: Dict) -> Dict:
    pass_result = None

    if _has_tag(raw_event, 1801):
        pass_result = PassResult.COMPLETE
    elif _has_tag(raw_event, 1802):
        pass_result = PassResult.INCOMPLETE

    if next_event:
        if next_event["eventName"] == 6:
            pass_result = PassResult.OFFSIDE
        elif next_event["eventName"] == 5 and next_event["subEventName"] == 50:
            pass_result = PassResult.OUT

    return {
        "result": pass_result,
        "qualifiers": _pass_qualifiers(raw_event),
        "receive_timestamp": None,
        "receiver_player": None,
        "receiver_coordinates": Point(**raw_event["positions"][1]),
    }


def _parse_foul(raw_event: Dict) -> Dict:
    return {"result": None, "qualifiers": None}


def _parse_card(raw_event: Dict) -> Dict:
    card_type = None
    if _has_tag(raw_event, 1701):
        card_type = CardType.RED
    elif _has_tag(raw_event, 1702):
        card_type = CardType.FIRST_YELLOW
    elif _has_tag(raw_event, 1703):
        card_type = CardType.SECOND_YELLOW

    return {"result": None, "qualifiers": None, "card_type": card_type}


def _parse_recovery(raw_event: Dict) -> Dict:
    return {
        "result": None,
        "qualifiers": None,
    }


def _parse_ball_out(raw_event: Dict) -> Dict:
    return {"result": None, "qualifiers": None}


def _parse_set_piece(raw_event: Dict, next_event: Dict) -> Dict:
    qualifiers = []

    result = {}

    if raw_event["subEventName"] in [30, 31, 32, 34, 36]:
        result = _parse_pass(raw_event, next_event)
        if raw_event["subEventName"] == 34:
            qualifiers.append(SetPieceQualifier(SetPieceType.GOAL_KICK))
        elif raw_event["subEventName"] == 36:
            qualifiers.append(SetPieceQualifier(SetPieceType.THROW_IN))
            qualifiers.append(PassQualifier(PassType.HAND_PASS))
        elif raw_event["subEventName"] in [31, 32]:
            qualifiers.append(SetPieceQualifier(SetPieceType.FREE_KICK))
        elif raw_event["subEventName"] == 30:
            qualifiers.append(SetPieceQualifier(SetPieceType.CORNER_KICK))
    elif raw_event["subEventName"] in [33, 35]:
        result = _parse_shot(raw_event, next_event)
        if raw_event["subEventName"] == 33:
            qualifiers.append(SetPieceQualifier(SetPieceType.FREE_KICK))
        elif raw_event["subEventName"] == 35:
            qualifiers.append(SetPieceQualifier(SetPieceType.PENALTY))
    else:
        print(raw_event["subEventName"])

    result["qualifiers"] = qualifiers
    return result


def _parse_takeon(raw_event: Dict) -> Dict:
    result = None
    if _has_tag(raw_event, 701):
        result = TakeOnResult.INCOMPLETE
    if _has_tag(raw_event, 703):
        result = TakeOnResult.COMPLETE

    return {"result": result, "qualifiers": None}


def _playersDict(players: List[Player]):
    return dict([(p.player_id, p) for p in players])


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

        periods = []

        with performance_logging("parse data", logger=logger):
            home_team_id, away_team_id = raw_events["teams"].keys()
            home_team = _parse_team(raw_events, home_team_id, Ground.HOME)
            away_team = _parse_team(raw_events, away_team_id, Ground.AWAY)
            teams = {home_team_id: home_team, away_team_id: away_team}
            players = dict(
                [
                    (wyId, _playersDict(team.players))
                    for wyId, team in teams.items()
                ]
            )

            events = []

            for idx, raw_event in enumerate(raw_events["events"]):
                next_event = None
                if (idx + 1) < len(raw_events["events"]):
                    next_event = raw_events["events"][idx + 1]

                team_id = str(raw_event["teamId"])
                player_id = str(raw_event["playerId"])

                if (
                    len(periods) == 0
                    or periods[-1].id != raw_event["matchPeriod"]
                ):
                    periods.append(
                        Period(
                            id=raw_event["matchPeriod"],
                            start_timestamp=0,
                            end_timestamp=0,
                        )
                    )

                generic_event_args = {
                    "event_id": raw_event["id"],
                    "raw_event": raw_event,
                    "coordinates": Point(**raw_event["positions"][0]),
                    "team": teams[team_id],
                    "player": players[team_id][player_id]
                    if player_id != "0"
                    else None,
                    "ball_owning_team": None,
                    "ball_state": None,
                    "period": periods[-1],
                    "timestamp": raw_event["eventSec"],
                }

                event = None
                if raw_event["eventName"] == 10:
                    shot_event_args = _parse_shot(raw_event, next_event)
                    event = [
                        ShotEvent.create(
                            **shot_event_args, **generic_event_args
                        )
                    ]
                elif raw_event["eventName"] == 8:
                    pass_event_args = _parse_pass(raw_event, next_event)
                    event = [
                        PassEvent.create(
                            **pass_event_args, **generic_event_args
                        )
                    ]
                elif raw_event["eventName"] == 2:
                    foul_event_args = _parse_foul(raw_event)
                    event = [
                        FoulCommittedEvent.create(
                            **foul_event_args, **generic_event_args
                        )
                    ]
                    if any(
                        (_has_tag(raw_event, t) for t in [1701, 1702, 1703])
                    ):
                        card_event_args = _parse_card(raw_event)
                        event.append(
                            CardEvent.create(
                                **card_event_args, **generic_event_args
                            )
                        )
                elif raw_event["eventName"] == 5:
                    ball_out_event_args = _parse_ball_out(raw_event)
                    event = [
                        BallOutEvent.create(
                            **ball_out_event_args, **generic_event_args
                        )
                    ]
                elif raw_event["eventName"] == 3:
                    set_piece_event_args = _parse_set_piece(
                        raw_event, next_event
                    )
                    if raw_event["subEventName"] in [30, 31, 32, 34, 36]:
                        event = [
                            PassEvent.create(
                                **set_piece_event_args, **generic_event_args
                            )
                        ]
                    elif raw_event["subEventName"] in [33, 35]:
                        event = [
                            ShotEvent.create(
                                **set_piece_event_args, **generic_event_args
                            )
                        ]
                    else:
                        print(raw_event["subEventName"])
                elif raw_event["eventName"] == 7:
                    recovery_event_args = _parse_recovery(raw_event)
                    event = [
                        RecoveryEvent.create(
                            **recovery_event_args, **generic_event_args
                        )
                    ]
                elif raw_event["eventName"] == 1:
                    takeon_event_args = _parse_takeon(raw_event)
                    event = [
                        TakeOnEvent.create(
                            **takeon_event_args, **generic_event_args
                        )
                    ]

                if event:
                    events.extend(event)

        metadata = Metadata(
            teams=teams.values(),
            periods=periods,
            pitch_dimensions=PitchDimensions(x_dim=100, y_dim=100),
            score=None,
            frame_rate=None,
            orientation=Orientation.BALL_OWNING_TEAM,
            flags=None,
            provider=Provider.WYSCOUT,
        )

        return EventDataset(metadata=metadata, records=events)

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
