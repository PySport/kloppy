from typing import Tuple, Dict, List, NamedTuple, IO
import logging
import json

from kloppy.domain import (
    EventDataset,
    Team,
    Point,
    BallState,
    Provider,
    PassEvent,
    ShotEvent,
    TakeOnEvent,
    CarryEvent,
    RecoveryEvent,
    FoulCommittedEvent,
    BallOutEvent,
    GenericEvent,
    PassResult,
    ShotResult,
    TakeOnResult,
    CarryResult,
    EventType,
    SetPieceType,
    SetPieceQualifier,
    BodyPart,
    BodyPartQualifier,
    Qualifier,
)
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer

from kloppy.infra.serializers.tracking.metrica_epts.metadata import (
    load_metadata,
    DeserializationError,
)
from kloppy.utils import performance_logging

logger = logging.getLogger(__name__)

# Passes
MS_PASS_OUTCOME_COMPLETE = 1
MS_PASS_OUTCOME_INCOMPLETE = 7
MS_PASS_OUTCOME_OUT = 6
MS_PASS_OUTCOME_OFFSIDE = 16

MS_WON = 48
MS_LOST = 49

MS_PASS_TYPES = [
    MS_PASS_OUTCOME_COMPLETE,
    MS_PASS_OUTCOME_INCOMPLETE,
    MS_PASS_OUTCOME_OUT,
    MS_PASS_OUTCOME_OFFSIDE,
]

# Set Pieces
MS_SET_PIECE = 5
MS_SET_PIECE_GOAL_KICK = 20
MS_SET_PIECE_FREE_KICK = 32
MS_SET_PIECE_THROW_IN = 34
MS_SET_PIECE_CORNER_KICK = 33
MS_SET_PIECE_PENALTY = 36
MS_SET_PIECE_KICK_OFF = 35

# Body Parts
MS_BODY_PART_HEAD = 11

# Shots
MS_EVENT_TYPE_SHOT = 2
MS_SHOT_OUTCOME_BLOCKED = 25
MS_SHOT_OUTCOME_GOAL = 30
MS_SHOT_OUTCOME_OFF_TARGET = 29
MS_SHOT_OUTCOME_POST = 27
MS_SHOT_OUTCOME_SAVED = 26

MS_SHOT_TYPES = [
    MS_EVENT_TYPE_SHOT,
    MS_SHOT_OUTCOME_BLOCKED,
    MS_SHOT_OUTCOME_GOAL,
    MS_SHOT_OUTCOME_OFF_TARGET,
    MS_SHOT_OUTCOME_POST,
    MS_SHOT_OUTCOME_SAVED,
]

# Others
MS_EVENT_TYPE_DRIBBLE = 45
MS_EVENT_TYPE_CARRY = 10
MS_EVENT_TYPE_CHALLENGE = 9
MS_EVENT_TYPE_RECOVERY = 3
MS_EVENT_TYPE_FOUL_COMMITTED = 4
MS_EVENT_TYPE_CARD = 8

OUT_EVENT_RESULTS = [PassResult.OUT]


def _parse_coordinates(event_start_or_end: dict) -> Point:
    x = event_start_or_end["x"]
    y = event_start_or_end["y"]
    if x is None:
        return None

    return Point(
        x=x,
        y=y,
    )


def _parse_subtypes(event: dict) -> List:
    if event["subtypes"]:
        if isinstance(event["subtypes"], list):
            return [subtype["id"] for subtype in event["subtypes"]]
        else:
            return [event["subtypes"]["id"]]
    else:
        return None


def _parse_pass(
    event: Dict, previous_event: Dict, subtypes: List, team: Team
) -> Dict:

    event_type_id = event["type"]["id"]

    if event_type_id == MS_PASS_OUTCOME_COMPLETE:
        result = PassResult.COMPLETE
        receiver_player = team.get_player_by_id(event["to"]["id"])
        receiver_coordinates = _parse_coordinates(event["end"])
        receive_timestamp = event["end"]["time"]
    else:
        if event_type_id == MS_PASS_OUTCOME_OUT:
            result = PassResult.OUT
        elif event_type_id == MS_PASS_OUTCOME_INCOMPLETE:
            if subtypes and MS_PASS_OUTCOME_OFFSIDE in subtypes:
                result = PassResult.OFFSIDE
            else:
                result = PassResult.INCOMPLETE
        else:
            raise DeserializationError(
                f"Unknown pass outcome: {event_type_id}"
            )

        receiver_player = None
        receiver_coordinates = None
        receive_timestamp = None

    qualifiers = _get_event_qualifiers(event, previous_event, subtypes)

    return dict(
        result=result,
        receiver_coordinates=receiver_coordinates,
        receiver_player=receiver_player,
        receive_timestamp=receive_timestamp,
        qualifiers=qualifiers,
    )


def _get_event_qualifiers(
    event: Dict, previous_event: Dict, subtypes: List
) -> List[Qualifier]:

    qualifiers = []

    qualifiers.extend(_get_event_setpiece_qualifiers(previous_event, subtypes))
    qualifiers.extend(_get_event_bodypart_qualifiers(subtypes))

    return qualifiers


def _get_event_setpiece_qualifiers(
    previous_event: Dict, subtypes: List
) -> List[Qualifier]:

    qualifiers = []
    previous_event_type_id = previous_event["type"]["id"]
    if previous_event_type_id == MS_SET_PIECE:
        set_piece_subtypes = _parse_subtypes(previous_event)
        if MS_SET_PIECE_CORNER_KICK in set_piece_subtypes:
            qualifiers.append(
                SetPieceQualifier(value=SetPieceType.CORNER_KICK)
            )
        elif MS_SET_PIECE_FREE_KICK in set_piece_subtypes:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.FREE_KICK))
        elif MS_SET_PIECE_PENALTY in set_piece_subtypes:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.PENALTY))
        elif MS_SET_PIECE_THROW_IN in set_piece_subtypes:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.THROW_IN))
        elif MS_SET_PIECE_KICK_OFF in set_piece_subtypes:
            qualifiers.append(SetPieceQualifier(value=SetPieceType.KICK_OFF))
    elif subtypes and MS_SET_PIECE_GOAL_KICK in subtypes:
        qualifiers.append(SetPieceQualifier(value=SetPieceType.GOAL_KICK))

    return qualifiers


def _get_event_bodypart_qualifiers(subtypes: List) -> List[Qualifier]:

    qualifiers = []
    if subtypes and MS_BODY_PART_HEAD in subtypes:
        qualifiers.append(BodyPartQualifier(value=BodyPart.HEAD))

    return qualifiers


def _parse_shot(event: Dict, previous_event: Dict, subtypes: List) -> Dict:
    if MS_SHOT_OUTCOME_OFF_TARGET in subtypes:
        result = ShotResult.OFF_TARGET
    elif MS_SHOT_OUTCOME_SAVED in subtypes:
        result = ShotResult.SAVED
    elif MS_SHOT_OUTCOME_POST in subtypes:
        result = ShotResult.POST
    elif MS_SHOT_OUTCOME_BLOCKED in subtypes:
        result = ShotResult.BLOCKED
    elif MS_SHOT_OUTCOME_GOAL in subtypes:
        result = ShotResult.GOAL
    else:
        raise DeserializationError(f"Unknown shot outcome")

    qualifiers = _get_event_qualifiers(event, previous_event, subtypes)

    return dict(result=result, qualifiers=qualifiers)


def _parse_carry(event: Dict) -> Dict:
    return dict(
        result=CarryResult.COMPLETE,
        end_coordinates=_parse_coordinates(event["end"]),
        end_timestamp=event["end"]["time"],
    )


def _parse_take_on(subtypes: List) -> Dict:
    if MS_WON in subtypes:
        result = TakeOnResult.COMPLETE
    else:
        result = TakeOnResult.INCOMPLETE

    return dict(result=result)


def _parse_ball_owning_team(event_type: int, team: Team) -> Team:
    if event_type not in [
        MS_EVENT_TYPE_CHALLENGE,
        MS_EVENT_TYPE_CARD,
    ]:
        return team
    else:
        return None


class MetricaJsonEventDataInputs(NamedTuple):
    meta_data: IO[bytes]
    event_data: IO[bytes]


class MetricaJsonEventDataDeserializer(
    EventDataDeserializer[MetricaJsonEventDataInputs]
):
    @property
    def provider(self) -> Provider:
        return Provider.METRICA

    def deserialize(self, inputs: MetricaJsonEventDataInputs) -> EventDataset:
        with performance_logging("load data", logger=logger):
            raw_events = json.load(inputs.event_data)
            metadata = load_metadata(
                inputs.meta_data, provider=Provider.METRICA
            )

            transformer = self.get_transformer(
                length=metadata.pitch_dimensions.length,
                width=metadata.pitch_dimensions.width,
            )

        with performance_logging("parse data", logger=logger):
            events = []
            for i, raw_event in enumerate(raw_events["data"]):

                if raw_event["team"]["id"] == metadata.teams[0].team_id:
                    team = metadata.teams[0]
                elif raw_event["team"]["id"] == metadata.teams[1].team_id:
                    team = metadata.teams[1]
                else:
                    raise DeserializationError(
                        f"Unknown team_id {raw_event['team']['id']}"
                    )

                player = team.get_player_by_id(raw_event["from"]["id"])
                event_type = raw_event["type"]["id"]
                subtypes = _parse_subtypes(raw_event)
                period = [
                    period
                    for period in metadata.periods
                    if period.id == raw_event["period"]
                ][0]
                previous_event = raw_events["data"][i - 1]

                generic_event_kwargs = dict(
                    # from DataRecord
                    period=period,
                    timestamp=raw_event["start"]["time"],
                    ball_owning_team=_parse_ball_owning_team(event_type, team),
                    ball_state=BallState.ALIVE,
                    # from Event
                    event_id=None,
                    team=team,
                    player=player,
                    coordinates=(_parse_coordinates(raw_event["start"])),
                    raw_event=raw_event,
                )

                iteration_events = []

                if event_type in MS_PASS_TYPES:
                    pass_event_kwargs = _parse_pass(
                        event=raw_event,
                        previous_event=previous_event,
                        subtypes=subtypes,
                        team=team,
                    )

                    event = self.event_factory.build_pass(
                        **pass_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_SHOT:
                    shot_event_kwargs = _parse_shot(
                        event=raw_event,
                        previous_event=previous_event,
                        subtypes=subtypes,
                    )
                    event = self.event_factory.build_shot(
                        **shot_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif subtypes and MS_EVENT_TYPE_DRIBBLE in subtypes:
                    take_on_event_kwargs = _parse_take_on(subtypes=subtypes)
                    event = self.event_factory.build_take_on(
                        qualifiers=None,
                        **take_on_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_CARRY:
                    carry_event_kwargs = _parse_carry(
                        event=raw_event,
                    )
                    event = self.event_factory.build_carry(
                        qualifiers=None,
                        **carry_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_RECOVERY:
                    event = self.event_factory.build_recovery(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_FOUL_COMMITTED:
                    event = self.event_factory.build_foul_committed(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )

                else:
                    event = self.event_factory.build_generic(
                        result=None,
                        qualifiers=None,
                        event_name=raw_event["type"]["name"],
                        **generic_event_kwargs,
                    )

                if self.should_include_event(event):
                    events.append(transformer.transform_event(event))

                # Checks if the event ended out of the field and adds a synthetic out event
                if event.result in OUT_EVENT_RESULTS:
                    generic_event_kwargs["ball_state"] = BallState.DEAD
                    if raw_event["end"]["x"]:
                        generic_event_kwargs[
                            "coordinates"
                        ] = _parse_coordinates(raw_event["end"])
                        generic_event_kwargs["timestamp"] = raw_event["end"][
                            "time"
                        ]

                        event = self.event_factory.build_ball_out(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )

                        if self.should_include_event(event):
                            events.append(transformer.transform_event(event))

        return EventDataset(
            metadata=metadata,
            records=events,
        )
