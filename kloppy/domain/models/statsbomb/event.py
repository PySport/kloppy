from dataclasses import dataclass

from kloppy.utils import docstring_inherit_attributes
from ..event import PassEvent, ShotEvent
from ... import EventFactory, create_event


@dataclass(repr=False)
@docstring_inherit_attributes(PassEvent)
class StatsbombPassEvent(PassEvent):
    """
    Attributes:

    """


@dataclass(repr=False)
@docstring_inherit_attributes(ShotEvent)
class StatsbombShotEvent(ShotEvent):
    """
    Attributes:

    """


class StatsbombEventFactory(EventFactory):
    def build_pass(self, **kwargs) -> StatsbombPassEvent:
        return create_event(StatsbombPassEvent, **kwargs)

    def build_shot(self, **kwargs) -> StatsbombShotEvent:
        return create_event(StatsbombShotEvent, **kwargs)
