"""Functions for loading Hudl StatsBomb event data."""

from ._providers.statsbomb import load, load_open_data

__all__ = ["load", "load_open_data"]
