import json
import logging
from typing import Dict, List, Tuple, Union, IO, NamedTuple

from kloppy.domain import (
    AttackingDirection,
    BallOutEvent,
    BallState,
    BodyPart,
    BodyPartQualifier,
    CardEvent,
    CardType,
    DatasetFlag,
    Event,
    EventDataset,
    FoulCommittedEvent,
    GenericEvent,
    Ground,
    Metadata,
    Orientation,
    PassEvent,
    PassResult,
    Period,
    Player,
    Point,
    Provider,
    Qualifier,
    RecoveryEvent,
    Score,
    SetPieceQualifier,
    SetPieceType,
    ShotEvent,
    ShotResult,
    SubstitutionEvent,
    Team,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import Readable, performance_logging


logger = logging.getLogger(__name__)


DF_EVENT_CLASS_STATUS = "status"
DF_EVENT_CLASS_NUTMEGS = "nutmegs"
DF_EVENT_CLASS_STEALINGS = "stealings"
DF_EVENT_CLASS_FOULS = "fouls"
DF_EVENT_CLASS_THROW_IN = "throwIn"
DF_EVENT_CLASS_INCORRECT_PASSES = "incorrectPasses"
DF_EVENT_CLASS_CLEARANCES = "clearances"
DF_EVENT_CLASS_CORRECT_PASSES = "correctPasses"
DF_EVENT_CLASS_SOMBRERO_FLICK = "sombreroFlick"
DF_EVENT_CLASS_GOALKICK = "goalkick"
DF_EVENT_CLASS_GOALS = "goals"
DF_EVENT_CLASS_SHOTS = "shots"
DF_EVENT_CLASS_OFFSIDES = "offsides"
DF_EVENT_CLASS_RED_CARDS = "redCards"
DF_EVENT_CLASS_YELLOW_CARDS = "yellowCards"
DF_EVENT_CLASS_SUBSTITUTIONS = "substitutions"
DF_EVENT_CLASS_PENALTY_SHOOTOUT = "penaltyShootout"
DF_EVENT_CLASS_CORNERKICKS = "cornerKicks"

DF_EVENT_CLASS_PASSES = {
    DF_EVENT_CLASS_THROW_IN,
    DF_EVENT_CLASS_INCORRECT_PASSES,
    DF_EVENT_CLASS_CORRECT_PASSES,
    DF_EVENT_CLASS_CORNERKICKS,
}
DF_EVENT_CLASS_CARDS = {DF_EVENT_CLASS_YELLOW_CARDS, DF_EVENT_CLASS_RED_CARDS}

# status event types
DF_EVENT_TYPE_STATUS_MATCH_START = 1
DF_EVENT_TYPE_STATUS_MATCH_END = 2
DF_EVENT_TYPE_STATUS_FIRST_HALF_END = 17
DF_EVENT_TYPE_STATUS_SECOND_HALF_START = 18
DF_EVENT_TYPE_STATUS_SECOND_HALF_END = 49
DF_EVENT_TYPE_STATUS_FIRST_EXTRA_START = 50
DF_EVENT_TYPE_STATUS_FIRST_EXTRA_END = 51
DF_EVENT_TYPE_STATUS_SECOND_EXTRA_START = 52
DF_EVENT_TYPE_STATUS_SECOND_EXTRA_END = 53
DF_EVENT_TYPE_STATUS_PENALTY_SHOOTOUT_START = 54

# card event types
DF_EVENT_TYPE_YELLOW_CARD = 3
DF_EVENT_TYPE_RED_CARD_DOUBLE_YELLOW = 4
DF_EVENT_TYPE_RED_CARD = 5

# shots
DF_EVENT_TYPE_SHOT_OPEN_PLAY_GOAL = 9
DF_EVENT_TYPE_SHOT_OWN_GOAL = 10
DF_EVENT_TYPE_SHOT_HEAD_GOAL = 11
DF_EVENT_TYPE_SHOT_FREE_KICK_GOAL = 12
DF_EVENT_TYPE_SHOT_PENALTY_GOAL = 13
DF_EVENT_TYPE_SHOT_OFF_TARGET = 33
DF_EVENT_TYPE_SHOT_POST = 34
DF_EVENT_TYPE_SHOT_SAVED = 35
DF_EVENT_TYPE_SHOT_PENALTY_SAVED = 43
DF_EVENT_TYPE_SHOT_PENALTY_OFF_TARGET = 44
DF_EVENT_TYPE_SHOT_PENALTY_POST = 45

GOAL_EVENTS = {
    DF_EVENT_TYPE_SHOT_OPEN_PLAY_GOAL,
    DF_EVENT_TYPE_SHOT_OWN_GOAL,
    DF_EVENT_TYPE_SHOT_HEAD_GOAL,
    DF_EVENT_TYPE_SHOT_FREE_KICK_GOAL,
    DF_EVENT_TYPE_SHOT_PENALTY_GOAL,
}

PENALTY_SHOT_EVENTS = {
    DF_EVENT_TYPE_SHOT_PENALTY_GOAL,
    DF_EVENT_TYPE_SHOT_PENALTY_SAVED,
    DF_EVENT_TYPE_SHOT_PENALTY_OFF_TARGET,
    DF_EVENT_TYPE_SHOT_PENALTY_POST,
}

# ball out events
DF_EVENT_TYPE_CORNER_KICK = 28
DF_EVENT_TYPE_THROW_IN = 46
DF_EVENT_TYPE_GOAL_KICK = 48

BALL_OUT_EVENTS = {
    DF_EVENT_TYPE_THROW_IN,
    DF_EVENT_TYPE_CORNER_KICK,
    DF_EVENT_TYPE_GOAL_KICK,
}

# stealings
DF_EVENT_TYPE_CLEARANCE = 29
DF_EVENT_TYPE_CLEARANCE_TO_CORNER = 30
DF_EVENT_TYPE_STEALING = 182

# fouls
DF_EVENT_TYPE_FOUL_PENALTY = 31
DF_EVENT_TYPE_HAND_PENALTY = 32
DF_EVENT_TYPE_FOUL = 36
DF_EVENT_TYPE_HAND = 37
DF_EVENT_TYPE_OFFSIDE = 47

FOUL_FREE_KICK_EVENTS = {
    DF_EVENT_TYPE_FOUL,
    DF_EVENT_TYPE_HAND,
}

# passes
DF_EVENT_TYPE_PASS_CORRECT = 180
DF_EVENT_TYPE_PASS_INCORRECT = 181

# misc
DF_EVENT_TYPE_NUTMEG = 507
DF_EVENT_TYPE_SOMBRERO_FLICK = 509
DF_EVENT_TYPE_PENALTY_SHOOTOUT_GOAL = 55
DF_EVENT_TYPE_PENALTY_SHOOTOUT_SAVED = 56
DF_EVENT_TYPE_PENALTY_SHOOTOUT_OFF_TARGET = 57
DF_EVENT_TYPE_PENALTY_SHOOTOUT_POST = 183


def parse_str_ts(raw_event: Dict) -> float:
    return raw_event["t"]["m"] * 60 + (raw_event["t"]["s"] or 0)


def _parse_coordinates(coordinates: Dict[str, float]) -> Point:
    # location is cell based
    # +-------+-------+
    # | -1,-1 |  1,-1 |
    # +-------+-------+
    # | -1,1  |  1,1  |
    # +-------+-------+
    return Point(x=coordinates["x"], y=coordinates["y"])


def _get_team_and_player(
    raw_event: Dict, home_team: Team, away_team: Team
) -> Tuple[Team, Player]:
    team = None
    player = None

    team_id = raw_event.get("team")
    if team_id is not None:
        team = home_team if str(team_id) == home_team.team_id else away_team

    if "plyrId" in raw_event:
        if team is not None:
            player = team.get_player_by_id(raw_event["plyrId"])
        else:
            # NOTE: sometime events are missing team
            player = home_team.get_player_by_id(raw_event["plyrId"])
            if player is not None:
                team = home_team
            else:
                player = away_team.get_player_by_id(raw_event["plyrId"])
                team = away_team
    return team, player


def _get_event_qualifiers(
    raw_event: Dict, previous_event: Dict = None
) -> List[Qualifier]:
    qualifiers = []

    if raw_event["type"] == DF_EVENT_TYPE_THROW_IN:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.THROW_IN))

    if raw_event["type"] == DF_EVENT_TYPE_CORNER_KICK:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.CORNER_KICK))

    if raw_event["type"] in PENALTY_SHOT_EVENTS:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.PENALTY))

    if raw_event["type"] == DF_EVENT_TYPE_SHOT_HEAD_GOAL:
        qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))

    if (
        previous_event is not None
        and previous_event["type"] == DF_EVENT_TYPE_GOAL_KICK
        and previous_event["plyrId"] == raw_event["plyrId"]
    ):
        qualifiers.append(SetPieceQualifier(value=SetPieceType.GOAL_KICK))

    if raw_event["type"] == DF_EVENT_TYPE_SHOT_FREE_KICK_GOAL or (
        previous_event is not None
        and previous_event["type"] in FOUL_FREE_KICK_EVENTS
    ):
        qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))

    if previous_event is None or previous_event["type"] in GOAL_EVENTS:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.KICK_OFF))

    return qualifiers


def _parse_pass(
    raw_event: Dict,
    team: Team,
    previous_event: Dict = None,
    next_event: Dict = None,
) -> Dict:
    if next_event is not None and next_event["type"] == DF_EVENT_TYPE_OFFSIDE:
        result = PassResult.OFFSIDE
    elif raw_event["type"] == DF_EVENT_TYPE_PASS_CORRECT:
        result = PassResult.COMPLETE
    elif next_event is not None and next_event["type"] in BALL_OUT_EVENTS:
        result = PassResult.OUT
    else:
        result = PassResult.INCOMPLETE

    receiver_coordinates = None
    # NOTE: in really rare cases coordinates may be missing
    coordinates = raw_event.get("coord", {}).get("2")
    if coordinates is not None:
        receiver_coordinates = _parse_coordinates(coordinates)

    # find receiver player, if possible
    receiver_player = None
    if "recvId" in raw_event:
        receiver_player = team.get_player_by_id(raw_event["recvId"])

    elif raw_event["type"] in (
        DF_EVENT_TYPE_THROW_IN,
        DF_EVENT_TYPE_CORNER_KICK,
    ):
        # there is no receiver data in this case, use next_event to deduce receiver
        if next_event is not None:
            if (
                next_event["team"] != raw_event["team"]
                and next_event["type"] == DF_EVENT_TYPE_FOUL
                and "recvId" in next_event
            ):
                # foul from the opposite team
                receiver_player = team.get_player_by_id(next_event["recvId"])
                result = PassResult.COMPLETE
            elif (
                next_event["team"] == raw_event["team"]
                and "plyrId" in next_event
            ):
                # or same team event with plyrId
                receiver_player = team.get_player_by_id(next_event["plyrId"])
                result = PassResult.COMPLETE

    qualifiers = _get_event_qualifiers(raw_event, previous_event)

    return dict(
        result=result,
        receiver_coordinates=receiver_coordinates,
        receiver_player=receiver_player,
        receive_timestamp=parse_str_ts(raw_event),
        qualifiers=qualifiers,
    )


def _parse_shot(raw_event: Dict, previous_event: Dict = None) -> Dict:
    outcome_id = raw_event["type"]
    if outcome_id in GOAL_EVENTS:
        result = ShotResult.GOAL
    elif outcome_id in (
        DF_EVENT_TYPE_SHOT_OFF_TARGET,
        DF_EVENT_TYPE_SHOT_PENALTY_OFF_TARGET,
    ):
        result = ShotResult.OFF_TARGET
    elif outcome_id in (
        DF_EVENT_TYPE_SHOT_POST,
        DF_EVENT_TYPE_SHOT_PENALTY_POST,
    ):
        result = ShotResult.POST
    elif outcome_id in (
        DF_EVENT_TYPE_SHOT_SAVED,
        DF_EVENT_TYPE_SHOT_PENALTY_SAVED,
    ):
        result = ShotResult.SAVED
    else:
        raise DeserializationError(f"Unknown shot outcome: {outcome_id}")

    qualifiers = _get_event_qualifiers(raw_event, previous_event)

    return dict(
        result=result,
        qualifiers=qualifiers,
    )


def _parse_card(raw_event: Dict) -> Dict:
    card_id = raw_event["type"]
    if card_id == DF_EVENT_TYPE_RED_CARD:
        card_type = CardType.RED
    elif card_id == DF_EVENT_TYPE_RED_CARD_DOUBLE_YELLOW:
        card_type = CardType.SECOND_YELLOW
    elif card_id == DF_EVENT_TYPE_YELLOW_CARD:
        card_type = CardType.FIRST_YELLOW
    else:
        raise DeserializationError(f"Unknown card id {card_id}")

    return dict(card_type=card_type)


def _parse_substitution(raw_event: Dict, team: Team) -> Dict:
    player = team.get_player_by_id(raw_event["offId"])
    replacement_player = team.get_player_by_id(raw_event["inId"])

    return dict(player=player, replacement_player=replacement_player)


def _include_event(event: Event, wanted_event_types: List) -> bool:
    return not wanted_event_types or event.event_type in wanted_event_types


class DatafactoryInputs(NamedTuple):
    event_data: IO[bytes]


class DatafactoryDeserializer(EventDataDeserializer[DatafactoryInputs]):
    @property
    def provider(self) -> Provider:
        return Provider.DATAFACTORY

    def deserialize(self, inputs: DatafactoryInputs) -> EventDataset:

        transformer = self.get_transformer(length=2, width=2)

        with performance_logging("load data", logger=logger):
            data = json.load(inputs.event_data)
            match = data["match"]
            score_data = data["scoreStatus"]
            incidences = data["incidences"]
            players_data = data["players"]
            teams_data = data["teams"]

        with performance_logging("parse data", logger=logger):
            teams = []
            scores = []
            team_ids = (
                (Ground.HOME, str(match["homeTeamId"])),
                (Ground.AWAY, str(match["awayTeamId"])),
            )
            for ground, team_id in team_ids:
                team = Team(
                    team_id=team_id,
                    name=teams_data[team_id]["name"],
                    ground=ground,
                )
                team.players = [
                    Player(
                        player_id=player_id,
                        team=team,
                        first_name=player["name"]["first"],
                        last_name=player["name"]["last"],
                        name=player["name"]["shortName"]
                        or player["name"]["nick"],
                        jersey_no=player["squadNo"],
                        starting=not player["substitute"],
                    )
                    for player_id, player in players_data.items()
                    if str(player["teamId"]) == team_id
                ]
                teams.append(team)
                scores.append(score_data.get(team_id, {}).get("score"))
            score = Score(home=scores[0], away=scores[1])

            # setup periods
            status = incidences.pop(DF_EVENT_CLASS_STATUS)
            # start timestamps are fixed
            start_ts = {1: 0, 2: 45 * 60, 3: 90 * 60, 4: 105 * 60, 5: 120 * 60}
            # check for end status updates to setup periods
            end_event_types = {
                DF_EVENT_TYPE_STATUS_MATCH_END,
                DF_EVENT_TYPE_STATUS_FIRST_HALF_END,
                DF_EVENT_TYPE_STATUS_SECOND_HALF_END,
                DF_EVENT_TYPE_STATUS_FIRST_EXTRA_END,
                DF_EVENT_TYPE_STATUS_SECOND_EXTRA_END,
            }
            periods = {}
            for status_update in status.values():
                if status_update["type"] not in end_event_types:
                    continue
                half = status_update["t"]["half"]
                end_ts = parse_str_ts(status_update)
                periods[half] = Period(
                    id=half,
                    start_timestamp=start_ts[half],
                    end_timestamp=end_ts,
                    attacking_direction=AttackingDirection.HOME_AWAY
                    if half % 2 == 1
                    else AttackingDirection.AWAY_HOME,
                )

            # exclude goals, already listed as shots too
            incidences.pop(DF_EVENT_CLASS_GOALS)
            raw_events = [
                (k, e_id, e)
                for k in incidences
                for e_id, e in incidences[k].items()
            ]
            # sort events by timestamp, event_id
            raw_events.sort(
                key=lambda e: (
                    e[2]["t"]["half"],
                    e[2]["t"]["m"],
                    e[2]["t"]["s"] or 0,
                    e[1],
                )
            )

            home_team, away_team = teams
            events = []
            previous_event = next_event = None
            for i, (e_class, e_id, raw_event) in enumerate(raw_events):
                period = periods.get(raw_event["t"]["half"])
                if period is None:
                    # skip invalid event
                    continue

                timestamp = parse_str_ts(raw_event)
                if (
                    previous_event is not None
                    and previous_event["t"]["half"] != raw_event["t"]["half"]
                ):
                    previous_event = None
                next_event = (
                    raw_events[i + 1][2] if i + 1 < len(raw_events) else None
                )

                team, player = _get_team_and_player(
                    raw_event, home_team, away_team
                )

                event_base_kwargs = dict(
                    # from DataRecord
                    period=period,
                    timestamp=timestamp,
                    ball_owning_team=team,
                    ball_state=BallState.ALIVE,
                    # from Event
                    event_id=e_id,
                    team=team,
                    player=player,
                    coordinates=(
                        _parse_coordinates(raw_event["coord"]["1"])
                        if "coord" in raw_event
                        else None
                    ),
                    raw_event=raw_event,
                    result=None,
                    qualifiers=None,
                )

                if e_class in DF_EVENT_CLASS_PASSES:
                    pass_event_kwargs = _parse_pass(
                        raw_event=raw_event,
                        team=team,
                        previous_event=previous_event,
                        next_event=next_event,
                    )
                    event_base_kwargs.update(pass_event_kwargs)
                    event = self.event_factory.build_pass(**event_base_kwargs)

                elif e_class == DF_EVENT_CLASS_SHOTS:
                    shot_event_kwargs = _parse_shot(
                        raw_event=raw_event,
                        previous_event=previous_event,
                    )
                    event_base_kwargs.update(shot_event_kwargs)
                    event = self.event_factory.build_shot(**event_base_kwargs)

                elif e_class == DF_EVENT_CLASS_STEALINGS:
                    event = self.event_factory.build_recovery(
                        **event_base_kwargs
                    )

                elif e_class == DF_EVENT_CLASS_FOULS:
                    # NOTE: could use qualifiers? (hand, foul, penalty?)
                    # switch possession team
                    event_base_kwargs["ball_owning_team"] = (
                        home_team if team == away_team else away_team
                    )
                    event = self.event_factory.build_foul_committed(
                        **event_base_kwargs
                    )

                elif e_class in DF_EVENT_CLASS_CARDS:
                    card_kwargs = _parse_card(
                        raw_event=raw_event,
                    )
                    event_base_kwargs.update(card_kwargs)
                    event = self.event_factory.build_card(**event_base_kwargs)

                elif e_class == DF_EVENT_CLASS_SUBSTITUTIONS:
                    substitution_event_kwargs = _parse_substitution(
                        raw_event=raw_event, team=team
                    )
                    event_base_kwargs.update(substitution_event_kwargs)
                    event = self.event_factory.build_substitution(
                        **event_base_kwargs
                    )

                else:
                    # otherwise, a generic event
                    event = self.event_factory.build_generic(
                        event_name=e_class,
                        **event_base_kwargs,
                    )

                # check if the event implies ball was out of the field and add a synthetic out event
                if raw_event["type"] in BALL_OUT_EVENTS:
                    ball_out_event = self.event_factory.build_ball_out(
                        # from DataRecord
                        period=period,
                        timestamp=timestamp,
                        ball_owning_team=team,
                        ball_state=BallState.DEAD,
                        # from Event
                        event_id=e_id,
                        team=team,
                        player=player,
                        coordinates=event.coordinates,
                        raw_event=raw_event,
                        result=None,
                        qualifiers=None,
                    )
                    if self.should_include_event(event):
                        events.append(
                            transformer.transform_event(ball_out_event)
                        )

                if self.should_include_event(event):
                    events.append(transformer.transform_event(event))

                # only consider as a previous_event a ball-in-play event
                if e_class not in (
                    DF_EVENT_CLASS_YELLOW_CARDS,
                    DF_EVENT_CLASS_RED_CARDS,
                    DF_EVENT_CLASS_SUBSTITUTIONS,
                    DF_EVENT_CLASS_PENALTY_SHOOTOUT,
                ):
                    previous_event = raw_event

        metadata = Metadata(
            teams=teams,
            periods=sorted(periods.values(), key=lambda p: p.id),
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=None,
            orientation=Orientation.HOME_TEAM,
            flags=DatasetFlag.BALL_OWNING_TEAM,
            score=score,
            provider=Provider.DATAFACTORY,
            coordinate_system=transformer.get_to_coordinate_system(),
        )

        return EventDataset(
            metadata=metadata,
            records=events,
        )
