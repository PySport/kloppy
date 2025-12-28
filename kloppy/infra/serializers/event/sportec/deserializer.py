from copy import copy
import logging
from typing import IO, NamedTuple

from lxml import objectify

from kloppy.domain import (
    DatasetFlag,
    EventDataset,
    EventType,
    Metadata,
    Orientation,
    PassResult,
    Period,
    Point,
    Provider,
)
from kloppy.exceptions import DeserializationError
from kloppy.infra.serializers.event.deserializer import EventDataDeserializer
from kloppy.utils import performance_logging

from . import specification as SPORTEC
from .helpers import parse_datetime
from .metadata import SportecMetadata, load_metadata

logger = logging.getLogger(__name__)


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
        # Load data from XML files
        with performance_logging("load data", logger=logger):
            match_root = objectify.fromstring(inputs.meta_data.read())
            event_root = objectify.fromstring(inputs.event_data.read())

            # Flatten XML structure
            raw_events = []
            for event_elm in parse_sportec_xml(event_root):
                raw_events.append(SPORTEC.event_decoder(event_elm))
            # Sort events
            raw_events.sort(
                key=lambda x: parse_datetime(x.raw_event["EventTime"])
            )

        # Parse metadata
        with performance_logging("parse metadata", logger=logger):
            meta: SportecMetadata = load_metadata(match_root)

        # Initialize coordinate system transformer
        transformer = self.get_transformer(
            pitch_length=meta.x_max, pitch_width=meta.y_max
        )

        # Create periods
        # We extract periods from the events, as the start/end times are
        # more accurate there than in the metadata.
        with performance_logging("parse periods", logger=logger):
            periods, orientation = self._parse_periods_and_orientation(
                raw_events, meta.teams
            )

        # Create events
        with performance_logging("parse events", logger=logger):
            events = []
            for i, raw_event in enumerate(raw_events):
                new_events = raw_event.set_refs(
                    periods,
                    meta.teams,
                    prev_events=(raw_events[max(0, i - 5) : i]),
                    next_events=(
                        raw_events[i + 1 : min(i + 6, len(raw_events) - 1)]
                    ),
                ).deserialize(self.event_factory)
                for event in new_events:
                    if self.should_include_event(event):
                        # Transform event to the coordinate system
                        event = transformer.transform_event(event)
                        events.append(event)

            # Post-process events
            self._update_pass_receiver_coordinates(events, transformer)

        metadata = Metadata(
            date=meta.date,
            game_week=int(meta.game_week),
            game_id=meta.game_id,
            officials=meta.officials,
            teams=meta.teams,
            periods=periods,
            pitch_dimensions=transformer.get_to_coordinate_system().pitch_dimensions,
            frame_rate=None,
            orientation=orientation,
            flags=DatasetFlag.BALL_STATE,
            score=meta.score,
            provider=Provider.SPORTEC,
            coordinate_system=transformer.get_to_coordinate_system(),
        )
        return EventDataset(metadata=metadata, records=events)

    def _parse_periods_and_orientation(self, raw_events, teams):
        # Collect kick-off and final whistle events
        half_start_events = {}
        half_end_events = {}
        for event in raw_events:
            set_piece_type = event.raw_event["SetPieceType"]
            event_type = event.raw_event["EventType"]
            # Kick-off
            if (
                set_piece_type is not None
                and SPORTEC.SET_PIECE_TYPE(set_piece_type)
                == SPORTEC.SET_PIECE_TYPE.KICK_OFF
            ):
                set_piece_attr = event.raw_event["extra"][set_piece_type]
                if "GameSection" in set_piece_attr:
                    period = SPORTEC.PERIOD(set_piece_attr["GameSection"])
                    half_start_events[period] = {
                        "EventTime": event.raw_event["EventTime"],
                        "TeamLeft": set_piece_attr.get("TeamLeft"),
                    }
                else:
                    # This is a kick-off after a goal was scored
                    pass
            # Final whistle
            elif (
                event_type is not None
                and SPORTEC.EVENT_TYPE(event_type)
                == SPORTEC.EVENT_TYPE.FINAL_WHISTLE
            ):
                event_attr = event.raw_event["extra"][event_type]
                period = SPORTEC.PERIOD(event_attr["GameSection"])
                half_end_events[period] = {
                    "EventTime": event.raw_event["EventTime"],
                }

        # Create periods
        periods = []
        for period_id, period_name in enumerate(SPORTEC.PERIOD, start=1):
            start_event = half_start_events.get(period_name, None)
            end_event = half_end_events.get(period_name, None)
            if (start_event is None) ^ (end_event is None):
                raise DeserializationError(
                    f"Failed to determine start and end time of period {period_id}."
                )
            if (start_event is None) and (end_event is None):
                continue
            start_timestamp = parse_datetime(start_event["EventTime"])
            end_timestamp = parse_datetime(end_event["EventTime"])
            period = Period(
                id=period_id,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
            periods.append(period)

        # Determine orientation from first half kick-off
        team_left = half_start_events[SPORTEC.PERIOD.FIRST_HALF]["TeamLeft"]
        orientation = (
            Orientation.HOME_AWAY
            if team_left == teams[0].team_id
            else Orientation.AWAY_HOME
        )
        return periods, orientation

    def _update_pass_receiver_coordinates(self, events, transformer):
        pass_events = [
            (i, e)
            for i, e in enumerate(events[:-1])
            if e.event_type == EventType.PASS
            and e.result == PassResult.COMPLETE
        ]

        for i, pass_event in pass_events:
            candidates = events[i + 1 : min(i + 5, len(events))]
            receiver = next(
                (
                    e
                    for e in candidates
                    if (e.player == pass_event.receiver_player)
                    and (e.coordinates is not None)
                ),
                None,
            )

            if receiver:
                coords = copy(receiver.coordinates)
                if (
                    "X-Source-Position" in receiver.raw_event
                    and "Y-Source-Position" in receiver.raw_event
                ):
                    raw = receiver.raw_event
                    temp = receiver.replace(
                        coordinates=Point(
                            x=float(raw["X-Source-Position"]),
                            y=float(raw["Y-Source-Position"]),
                        )
                    )
                    coords = transformer.transform_event(temp).coordinates

                pass_event.receiver_coordinates = coords


def parse_sportec_xml(root: objectify.ObjectifiedElement) -> list[dict]:
    """Parses Sportec XML content into a structured list of event dictionaries.

    This function iterates through 'Event' elements in the provided XML. For each event,
    it extracts top-level attributes and recursively traverses child elements to
    categorize the event hierarchy and collect nested attributes into a specific format.

    The resulting dictionary for each event follows this structure:
        - Root keys: Attributes from the <Event> tag (e.g., 'EventId', 'EventTime', 'X-Position').
        - 'SetPieceType': The specific set piece context (e.g., 'KickOff', 'CornerKick'), if present.
        - 'EventType': The primary action type (e.g., 'Play', 'TacklingGame').
        - 'SubEventType': The specific action detail (e.g., 'Pass', 'Cross'), if present.
        - 'extra': A nested dictionary containing attributes of all child tags, keyed by
          the tag name (e.g., {'Play': {...}, 'Pass': {...}}).

    Args:
        root (objectify.ObjectifiedElement): The root element of the Sportec XML data.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a single
            parsed event.
    """
    # Define tags that indicate a set piece context
    SET_PIECE_TAGS = {sp.value for sp in SPORTEC.SET_PIECE_TYPE}

    # Helper to convert "true"/"false" strings to actual booleans
    def convert_value(val):
        if val.lower() == "true":
            return True
        elif val.lower() == "false":
            return False
        return val

    events_list = []

    # Iterate over each <Event> element
    for event in root.Event:
        # 1. Initialize the root dict with <Event> attributes
        event_data = {k: convert_value(v) for k, v in event.attrib.items()}

        # Initialize hierarchy placeholders
        event_data.update(
            {
                "SetPieceType": None,
                "EventType": None,
                "SubEventType": None,
                "extra": {},
            }
        )

        # Track the sequence of tags found to determine hierarchy later
        hierarchy_tags = []

        # 2. Recursive function to traverse children
        def traverse(element):
            # iterchildren() iterates over direct children in document order
            for child in element.iterchildren():
                tag = child.tag
                hierarchy_tags.append(tag)

                # Store attributes in 'extra' keyed by the tag name
                converted_attrs = {
                    k: convert_value(v) for k, v in child.attrib.items()
                }
                event_data["extra"][child.tag] = converted_attrs

                # Go deeper
                traverse(child)

        traverse(event)

        # 3. Map the tags to the Type fields
        if hierarchy_tags:
            first_tag = hierarchy_tags[0]

            if first_tag in SET_PIECE_TAGS:
                # Structure: [SetPiece] -> [Event] -> [SubEvent]
                event_data["SetPieceType"] = first_tag
                if len(hierarchy_tags) > 1:
                    event_data["EventType"] = hierarchy_tags[1]
                if len(hierarchy_tags) > 2:
                    event_data["SubEventType"] = hierarchy_tags[2]
            else:
                # Structure: [Event] -> [SubEvent]
                event_data["EventType"] = first_tag
                if len(hierarchy_tags) > 1:
                    event_data["SubEventType"] = hierarchy_tags[1]

        events_list.append(event_data)

    return events_list
