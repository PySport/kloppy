"""Functions for loading SciSports EPTS tracking data."""

from ._providers.scisports import load_tracking_epts as load_tracking

__all__ = ["load_tracking"]
