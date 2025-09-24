from dataclasses import dataclass

from kloppy.utils import docstring_inherit_attributes
from ..event import PassEvent, ShotEvent
from ... import EventFactory, create_event


@dataclass(repr=False)
@docstring_inherit_attributes(PassEvent)
class SciSportsPassEvent(PassEvent):
    """
    Attributes:

    """


@dataclass(repr=False)
@docstring_inherit_attributes(ShotEvent)
class SciSportsShotEvent(ShotEvent):
    """
    Attributes:

    """


class SciSportsEventFactory(EventFactory):
    def build_pass(self, **kwargs) -> SciSportsPassEvent:
        return create_event(SciSportsPassEvent, **kwargs)

    def build_shot(self, **kwargs) -> SciSportsShotEvent:
        return create_event(SciSportsShotEvent, **kwargs)
