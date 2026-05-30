from datetime import timedelta
from typing import Optional

from kloppy.domain import (
    BodyPart,
    CarryResult,
    ClearanceEvent,
    DuelEvent,
    EventDataset,
    EventFactory,
    GenericEvent,
    GoalkeeperEvent,
    InterceptionEvent,
    MiscontrolEvent,
    PassEvent,
    PressureEvent,
    RecoveryEvent,
    SetPieceQualifier,
    ShotEvent,
    TakeOnEvent,
    Unit,
)

from .base import DatasetMutator
from .helpers.insert import insert_record

VALID_EVENT = (
    PassEvent,
    ShotEvent,
    TakeOnEvent,
    ClearanceEvent,
    InterceptionEvent,
    DuelEvent,
    RecoveryEvent,
    MiscontrolEvent,
    GoalkeeperEvent,
)


class SyntheticCarryMutator(DatasetMutator[EventDataset]):
    def __init__(
        self,
        *,
        event_factory: Optional[EventFactory] = None,
        min_length_meters: float = 3,
        max_length_meters: float = 60,
        max_duration: timedelta = timedelta(seconds=10),
        inplace: bool = False,
    ):
        super().__init__(inplace=inplace)
        self.event_factory = event_factory or EventFactory()
        self.min_length_meters = min_length_meters
        self.max_length_meters = max_length_meters
        self.max_duration = max_duration

    def _mutate_inplace(self, dataset: EventDataset) -> EventDataset:
        pitch = dataset.metadata.pitch_dimensions
        events = dataset.records

        i = 0
        while i < len(events) - 1:
            event = events[i]

            if not isinstance(event, VALID_EVENT):
                i += 1
                continue

            j = i + 1
            while j < len(events) and isinstance(
                events[j], (GenericEvent, PressureEvent)
            ):
                j += 1

            if j >= len(events):
                break

            next_event = events[j]

            if not isinstance(next_event, VALID_EVENT):
                i += 1
                continue
            if event.team.team_id != next_event.team.team_id:
                i += 1
                continue
            if next_event.get_qualifier_value(SetPieceQualifier) is not None:
                i += 1
                continue

            if hasattr(event, "end_coordinates"):
                last_coord = event.end_coordinates
            elif hasattr(event, "receiver_coordinates"):
                last_coord = event.receiver_coordinates
            else:
                last_coord = event.coordinates

            new_coord = next_event.coordinates
            distance = pitch.distance_between(
                new_coord, last_coord, Unit.METERS
            )

            if not (
                self.min_length_meters <= distance <= self.max_length_meters
            ):
                i += 1
                continue

            dt = next_event.timestamp - event.timestamp
            if (
                dt > self.max_duration
                or event.period.id != next_event.period.id
            ):
                i += 1
                continue

            if isinstance(next_event, ShotEvent) and any(
                q.name == "body_part"
                and q.value in (BodyPart.HEAD, BodyPart.HEAD_OTHER)
                for q in next_event.qualifiers or []
            ):
                i += 1
                continue

            if getattr(event, "end_timestamp", None):
                last_timestamp = event.end_timestamp
            elif getattr(event, "receive_timestamp", None):
                last_timestamp = event.receive_timestamp
            else:
                last_timestamp = (
                    event.timestamp
                    + (next_event.timestamp - event.timestamp) / 10
                )

            generic_args = {
                "event_id": f"carry-{event.event_id}",
                "coordinates": last_coord,
                "team": next_event.team,
                "player": next_event.player,
                "ball_owning_team": next_event.ball_owning_team,
                "ball_state": event.ball_state,
                "period": next_event.period,
                "timestamp": last_timestamp,
                "raw_event": None,
            }

            carry_args = {
                "result": CarryResult.COMPLETE,
                "qualifiers": None,
                "end_coordinates": new_coord,
                "end_timestamp": next_event.timestamp,
            }

            carry = self.event_factory.build_carry(**carry_args, **generic_args)

            # use generic insert_record helper
            insert_record(dataset, carry, position=j)

            i = j + 1

        return dataset
