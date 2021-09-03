# detect if we are imported from the setup procedure (borrowed from numpy code)
try:
    __KLOPPY_SETUP__
except NameError:
    __KLOPPY_SETUP__ = False

if not __KLOPPY_SETUP__:
    from .infra.serializers import *
    from .helpers import *
    from .infra import datasets
    from .domain.services.matchers.pattern import (
        event as event_pattern_matching,
    )
    from .domain.services.state_builder import add_state

__version__ = "2.1.0"
