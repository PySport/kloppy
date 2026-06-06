from dataclasses import dataclass

from kloppy.utils import docstring_inherit_attributes

from ... import EventFactory, create_event
from ..event import PassEvent, ShotEvent


@dataclass(repr=False)
@docstring_inherit_attributes(PassEvent)
class StatsBombPassEvent(PassEvent):
    """
    Attributes:

    """


@dataclass(repr=False)
@docstring_inherit_attributes(ShotEvent)
class StatsBombShotEvent(ShotEvent):
    """
    Attributes:

    """


class StatsBombEventFactory(EventFactory):
    def build_pass(self, **kwargs) -> StatsBombPassEvent:
        return create_event(StatsBombPassEvent, **kwargs)

    def build_shot(self, **kwargs) -> StatsBombShotEvent:
        return create_event(StatsBombShotEvent, **kwargs)
