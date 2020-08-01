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
    GenericEvent,
    PassResult,
    ShotResult,
    TakeOnResult,
    CarryResult,
    EventType,
)

from kloppy.infra.serializers.event import EventDataSerializer
from kloppy.infra.serializers.tracking.epts.metadata import load_metadata
from kloppy.infra.utils import Readable, performance_logging

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
MS_EVENT_TYPE_CARD = 8


def _parse_coordinates(event_start_or_end: dict) -> Point:
    x = event_start_or_end["x"]
    y = event_start_or_end["y"]
    if x is None:
        return None

    return Point(x=x, y=y,)


def _parse_subtypes(event: dict) -> List:
    if event["subtypes"]:
        if isinstance(event["subtypes"], list):
            return [subtype["id"] for subtype in event["subtypes"]]
        else:
            return [event["subtypes"]["id"]]
    else:
        return None


def _parse_pass(event: Dict, subtypes: List, team: Team) -> Dict:

    pass_type_id = event["type"]["id"]

    if pass_type_id == MS_PASS_OUTCOME_COMPLETE:
        result = PassResult.COMPLETE
        receiver_player = team.get_player_by_id(event["to"]["id"])
        receiver_coordinates = _parse_coordinates(event["end"])
        receive_timestamp = event["end"]["time"]
    else:
        if pass_type_id == MS_PASS_OUTCOME_OUT:
            result = PassResult.OUT
        elif pass_type_id == MS_PASS_OUTCOME_INCOMPLETE:
            if subtypes and MS_PASS_OUTCOME_OFFSIDE in subtypes:
                result = PassResult.OFFSIDE
            else:
                result = PassResult.INCOMPLETE
        else:
            raise Exception(f"Unknown pass outcome: {pass_type_id}")

        receiver_player = None
        receiver_coordinates = None
        receive_timestamp = None

    return dict(
        result=result,
        receiver_coordinates=receiver_coordinates,
        receiver_player=receiver_player,
        receive_timestamp=receive_timestamp,
    )


def _parse_shot(event: Dict, subtypes: List) -> Dict:
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

    return dict(result=result)


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

        with performance_logging("parse data", logger=logger):

            wanted_event_types = [
                EventType[event_type.upper()]
                for event_type in options.get("event_types", [])
            ]

            events = []
            for raw_event in raw_events["data"]:
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

                if event_type in MS_PASS_TYPES:
                    pass_event_kwargs = _parse_pass(
                        event=raw_event, subtypes=subtypes, team=team,
                    )
                    event = PassEvent(
                        **pass_event_kwargs, **generic_event_kwargs,
                    )

                elif event_type == MS_EVENT_TYPE_SHOT:
                    shot_event_kwargs = _parse_shot(
                        event=raw_event, subtypes=subtypes
                    )
                    event = ShotEvent(
                        **shot_event_kwargs, **generic_event_kwargs
                    )

                elif subtypes and MS_EVENT_TYPE_DRIBBLE in subtypes:
                    take_on_event_kwargs = _parse_take_on(subtypes=subtypes)
                    event = TakeOnEvent(
                        **take_on_event_kwargs, **generic_event_kwargs
                    )
                elif event_type == MS_EVENT_TYPE_CARRY:
                    carry_event_kwargs = _parse_carry(event=raw_event,)
                    event = CarryEvent(
                        **carry_event_kwargs, **generic_event_kwargs,
                    )
                else:
                    event = GenericEvent(
                        result=None,
                        event_name=raw_event["type"]["name"],
                        **generic_event_kwargs,
                    )

                if (
                    not wanted_event_types
                    or event.event_type in wanted_event_types
                ):
                    events.append(event)

        return EventDataset(metadata=metadata, records=events,)

    def serialize(self, data_set: EventDataset) -> Tuple[str, str]:
        raise NotImplementedError
