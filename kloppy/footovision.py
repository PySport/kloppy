"""Functions for loading Footovision event and tracking data."""

from ._providers.footovision import load_event, load_tracking

__all__ = ["load_event", "load_tracking"]
