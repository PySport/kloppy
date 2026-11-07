"""Functions for loading Wyscout event and tracking data."""

from ._providers.wyscout import (
    load,
    load_event,
    load_open_data,
    load_tracking,
)

__all__ = ["load", "load_event", "load_open_data", "load_tracking"]
