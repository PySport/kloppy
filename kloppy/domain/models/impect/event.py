from dataclasses import dataclass

from kloppy.utils import docstring_inherit_attributes
from ..event import PassEvent, ShotEvent
from ... import EventFactory, create_event


@dataclass(repr=False)
@docstring_inherit_attributes(PassEvent)
class ImpectPassEvent(PassEvent):
    """
    Attributes:

    """


@dataclass(repr=False)
@docstring_inherit_attributes(ShotEvent)
class ImpectShotEvent(ShotEvent):
    """
    Attributes:

    """


class ImpectEventFactory(EventFactory):
    def build_pass(self, **kwargs) -> ImpectPassEvent:
        return create_event(ImpectPassEvent, **kwargs)

    def build_shot(self, **kwargs) -> ImpectShotEvent:
        return create_event(ImpectShotEvent, **kwargs)
