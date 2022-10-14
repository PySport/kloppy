import warnings
from dataclasses import fields
from typing import TypeVar, Type

from kloppy.domain import (
    PassEvent,
    ShotEvent,
    GenericEvent,
    TakeOnEvent,
    RecoveryEvent,
    CarryEvent,
    FormationChangeEvent,
    BallOutEvent,
    PlayerOnEvent,
    PlayerOffEvent,
    FoulCommittedEvent,
    CardEvent,
    SubstitutionEvent,
)

T = TypeVar("T")


def create_event(event_cls: Type[T], **kwargs) -> T:
    """
    Do the actual construction of an event.

    This method does a couple of things:
    1. Fill in some arguments when not passed
    2. Pass only arguments that are accepted by the `event_cls`.
       This is required in cases an EventFactory initialized less rich
       Events than data is passed for. E.g. `expected_goal` is passed
       to a regular `ShotEvent`.
       Normally this would break because of an 'Unexpected argument' exception,
       but we filter those arguments out.
    """
    extra_kwargs = {"state": {}}
    if "related_event_ids" not in kwargs:
        extra_kwargs["related_event_ids"] = []

    all_kwargs = dict(**kwargs, **extra_kwargs)

    relevant_kwargs = {
        field.name: all_kwargs.get(field.name, field.default)
        for field in fields(event_cls)
        if field.init
    }

    if len(relevant_kwargs) < len(all_kwargs):
        skipped_kwargs = set(all_kwargs.keys()) - set(relevant_kwargs.keys())
        warnings.warn(
            f"The following arguments were skipped: {skipped_kwargs}"
        )

    return event_cls(**relevant_kwargs)


class EventFactory:
    def build_pass(self, **kwargs) -> PassEvent:
        return create_event(PassEvent, **kwargs)

    def build_shot(self, **kwargs) -> ShotEvent:
        return create_event(ShotEvent, **kwargs)

    def build_generic(self, **kwargs) -> GenericEvent:
        return create_event(GenericEvent, **kwargs)

    def build_recovery(self, **kwargs) -> RecoveryEvent:
        return create_event(RecoveryEvent, **kwargs)

    def build_take_on(self, **kwargs) -> TakeOnEvent:
        return create_event(TakeOnEvent, **kwargs)

    def build_carry(self, **kwargs) -> CarryEvent:
        return create_event(CarryEvent, **kwargs)

    def build_formation_change(self, **kwargs) -> FormationChangeEvent:
        return create_event(FormationChangeEvent, **kwargs)

    def build_ball_out(self, **kwargs) -> BallOutEvent:
        return create_event(BallOutEvent, **kwargs)

    def build_player_on(self, **kwargs) -> PlayerOnEvent:
        return create_event(PlayerOnEvent, **kwargs)

    def build_player_off(self, **kwargs) -> PlayerOffEvent:
        return create_event(PlayerOffEvent, **kwargs)

    def build_card(self, **kwargs) -> CardEvent:
        return create_event(CardEvent, **kwargs)

    def build_foul_committed(self, **kwargs) -> FoulCommittedEvent:
        return create_event(FoulCommittedEvent, **kwargs)

    def build_substitution(self, **kwargs) -> SubstitutionEvent:
        return create_event(SubstitutionEvent, **kwargs)
