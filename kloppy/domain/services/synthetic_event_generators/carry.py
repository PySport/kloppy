import uuid
from datetime import timedelta
from typing import Optional

from kloppy.domain import (
    EventDataset,
    EventType,
    BodyPart,
    CarryResult,
    Unit,
    EventFactory,
)
from kloppy.domain.services.synthetic_event_generators.synthetic_event_generator import (
    SyntheticEventGenerator,
)


class SyntheticCarryGenerator(SyntheticEventGenerator):
    def __init__(self, event_factory: Optional[EventFactory] = None, **kwargs):
        self.event_factory = event_factory or EventFactory()
        self.min_length_meters = kwargs.get("min_length_meters") or 3
        self.max_length_meters = kwargs.get("max_length_meters") or 60
        self.max_duration = kwargs.get("max_duration") or timedelta(seconds=10)

    def add_synthetic_event(self, dataset: EventDataset):
        pitch = dataset.metadata.pitch_dimensions

        valid_event_types = [
            EventType.PASS,
            EventType.SHOT,
            EventType.TAKE_ON,
            EventType.CLEARANCE,
            EventType.INTERCEPTION,
            EventType.DUEL,
            EventType.RECOVERY,
            EventType.MISCONTROL,
            EventType.GOALKEEPER,
        ]

        for idx, event in enumerate(dataset.events):
            if event.event_type not in valid_event_types:
                continue
            idx_plus = 1
            go_to_next_event = True
            while idx + idx_plus < len(dataset.events) and go_to_next_event:
                next_event = dataset.events[idx + idx_plus]

                if next_event.event_type in [
                    EventType.GENERIC,
                    EventType.PRESSURE,
                ]:
                    idx_plus += 1
                    continue
                else:
                    go_to_next_event = False
                if not event.team.team_id == next_event.team.team_id:
                    continue

                if next_event.event_type not in valid_event_types:
                    continue

                if hasattr(event, "end_coordinates"):
                    last_coord = event.end_coordinates
                elif hasattr(event, "receiver_coordinates"):
                    last_coord = event.receiver_coordinates
                else:
                    last_coord = event.coordinates

                new_coord = next_event.coordinates

                distance_meters = pitch.distance_between(
                    new_coord, last_coord, Unit.METERS
                )
                # Not far enough
                if distance_meters < self.min_length_meters:
                    continue
                # Too far
                if distance_meters > self.max_length_meters:
                    continue

                dt = next_event.timestamp - event.timestamp
                # not same phase
                if dt > self.max_duration:
                    continue
                # not same period
                if not event.period.id == next_event.period.id:
                    continue

                # not headed shot
                if next_event.event_type == EventType.SHOT and any(
                    qualifier.name == "body_part"
                    and qualifier.value in [BodyPart.HEAD, BodyPart.HEAD_OTHER]
                    for qualifier in next_event.qualifiers or []
                ):
                    continue

                if hasattr(event, "end_timestamp"):
                    last_timestamp = event.end_timestamp
                elif hasattr(event, "receive_timestamp"):
                    last_timestamp = event.receive_timestamp
                else:
                    last_timestamp = (
                        event.timestamp
                        + (next_event.timestamp - event.timestamp) / 10
                    )
                generic_event_args = {
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
                carry_event_args = {
                    "result": CarryResult.COMPLETE,
                    "qualifiers": None,
                    "end_coordinates": new_coord,
                    "end_timestamp": next_event.timestamp,
                }
                new_carry = self.event_factory.build_carry(
                    **carry_event_args, **generic_event_args
                )
                dataset.records.insert(idx + idx_plus, new_carry)
