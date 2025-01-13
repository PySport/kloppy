import bisect
import uuid
from datetime import timedelta

from kloppy.domain import (
    EventDataset,
    EventType,
    BodyPart,
    CarryResult,
    EventFactory,
    Unit,
)
from kloppy.domain.services.synthetic_event_generators.synthetic_event_generator import (
    SyntheticEventGenerator,
)


class SyntheticCarryGenerator(SyntheticEventGenerator):
    min_length_meters = 3
    max_length_meters = 60
    max_duration = timedelta(seconds=10)

    def __init__(self, event_factory):
        self.event_factory = event_factory

    def add_synthetic_event(self, dataset: EventDataset):
        pitch = dataset.metadata.pitch_dimensions

        new_carries = []

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
            generic_next_event = True
            while idx + idx_plus < len(dataset.events) and generic_next_event:
                next_event = dataset.events[idx + idx_plus]

                if next_event.event_type in [
                    EventType.GENERIC,
                    EventType.PRESSURE,
                ]:
                    idx_plus += 1
                    continue
                else:
                    generic_next_event = False
                if not event.team.team_id == next_event.team.team_id:
                    continue

                if next_event.event_type not in valid_event_types:
                    continue
                # not headed shot
                if (
                    (hasattr(next_event, "body_part"))
                    and (next_event.event_type == EventType.SHOT)
                    and (
                        next_event.body_part.type.isin(
                            [BodyPart.HEAD, BodyPart.HEAD_OTHER]
                        )
                    )
                ):
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

                if hasattr(event, "end_timestamp"):
                    last_timestamp = event.end_timestamp + timedelta(
                        seconds=0.1
                    )
                elif hasattr(event, "receive_timestamp"):
                    last_timestamp = event.receive_timestamp + timedelta(
                        seconds=0.1
                    )
                else:
                    last_timestamp = (
                        event.timestamp
                        + (next_event.timestamp - event.timestamp) / 10
                    )

                generic_event_args = {
                    "event_id": f"{str(uuid.uuid4())}",
                    "coordinates": last_coord,
                    "team": next_event.team,
                    "player": next_event.player,
                    "ball_owning_team": next_event.ball_owning_team,
                    "ball_state": event.ball_state,
                    "period": next_event.period,
                    "timestamp": last_timestamp,
                    "raw_event": {},
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
                new_carries.append(new_carry)

        for new_carry in new_carries:
            pos = bisect.bisect_left(
                [e.time for e in dataset.events], new_carry.time
            )
            dataset.records.insert(pos, new_carry)
