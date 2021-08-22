from typing import Tuple, Dict, List
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
    Event,
    build_coordinate_system,
    Transformer,
)

from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.infra.serializers.tracking.epts.metadata import load_metadata
from kloppy.utils import Readable, performance_logging

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
            raise Exception(f"Unknown pass outcome: {event_type_id}")

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
        raise Exception(f"Unknown shot outcome")

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


def _include_event(event: Event, wanted_event_types: List) -> bool:
    return not wanted_event_types or event.event_type in wanted_event_types


class MetricaEventsJsonSerializer(EventDataSerializer):
    @staticmethod
    def __validate_inputs(inputs: Dict[str, Readable]):
        if "event_data" not in inputs:
            raise ValueError("Please specify a value for input 'event_data'")
        if "metadata" not in inputs:
            raise ValueError("Please specify a value for input 'metadata'")

    def deserialize(
        self, inputs: Dict[str, Readable], options: Dict = None
    ) -> EventDataset:
        """
                Deserialize Metrica Sports event data json format into a `EventDataset`.

                Parameters
                ----------
                inputs : dict
                    input `event_data` should point to a `Readable` object containing
                    the 'json' formatted event data. input `metadata` should point
                    to a `Readable` object containing the `xml` metadata file.
                options : dict
                    Options for deserialization of the Metrica Sports event json file.
                    Possible options are `event_types` (list of event types) to specify
                    the event types that should be returned. Valid types: "shot", "pass",
                    "carry", "take_on" and "generic". Generic is everything other than
                    the first 4. Those events are barely parsed. This type of event can
                    be used to do the parsing yourself.
                    Every event has a 'raw_event' attribute which contains the original
                    dictionary.
                Returns
                -------
                dataset : EventDataset
                Raises
                ------

                See Also
                --------

                Examples
                --------
                >>> serializer = MetricaEventsJsonSerializer()
                >>> with open("events.json", "rb") as event_data, \
                >>>      open("metadata.xml", "rb") as metadata:
                >>>
                >>>     dataset = serializer.deserialize(
                >>>         inputs={
                >>>             'event_data': event_data,
                >>>             'metadata': metadata
                >>>         },
                >>>         options={
                >>>             'event_types': ["pass", "take_on", "carry", "shot"]
                >>>         }
                >>>     )
                """
        self.__validate_inputs(inputs)
        if not options:
            options = {}

        with performance_logging("load data", logger=logger):
            raw_events = json.load(inputs["event_data"])
            metadata = load_metadata(
                inputs["metadata"], provider=Provider.METRICA
            )

            to_coordinate_system = build_coordinate_system(
                options.get("coordinate_system", Provider.KLOPPY),
                length=metadata.pitch_dimensions.length,
                width=metadata.pitch_dimensions.width,
            )

            transformer = Transformer(
                from_coordinate_system=metadata.coordinate_system,
                to_coordinate_system=to_coordinate_system,
            )

        with performance_logging("parse data", logger=logger):

            wanted_event_types = [
                EventType[event_type.upper()]
                for event_type in options.get("event_types", [])
            ]

            events = []
            for i, raw_event in enumerate(raw_events["data"]):

                if raw_event["team"]["id"] == metadata.teams[0].team_id:
                    team = metadata.teams[0]
                elif raw_event["team"]["id"] == metadata.teams[1].team_id:
                    team = metadata.teams[1]
                else:
                    raise Exception(
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

                    event = PassEvent.create(
                        **pass_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_SHOT:
                    shot_event_kwargs = _parse_shot(
                        event=raw_event,
                        previous_event=previous_event,
                        subtypes=subtypes,
                    )
                    event = ShotEvent.create(
                        **shot_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif subtypes and MS_EVENT_TYPE_DRIBBLE in subtypes:
                    take_on_event_kwargs = _parse_take_on(subtypes=subtypes)
                    event = TakeOnEvent.create(
                        qualifiers=None,
                        **take_on_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_CARRY:
                    carry_event_kwargs = _parse_carry(
                        event=raw_event,
                    )
                    event = CarryEvent.create(
                        qualifiers=None,
                        **carry_event_kwargs,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_RECOVERY:
                    event = RecoveryEvent.create(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_FOUL_COMMITTED:
                    event = FoulCommittedEvent.create(
                        result=None,
                        qualifiers=None,
                        **generic_event_kwargs,
                    )

                else:
                    event = GenericEvent.create(
                        result=None,
                        qualifiers=None,
                        event_name=raw_event["type"]["name"],
                        **generic_event_kwargs,
                    )

                if _include_event(event, wanted_event_types):
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

                        event = BallOutEvent.create(
                            result=None,
                            qualifiers=None,
                            **generic_event_kwargs,
                        )

                        if _include_event(event, wanted_event_types):
                            events.append(transformer.transform_event(event))

        return EventDataset(
            metadata=metadata,
            records=events,
        )

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
