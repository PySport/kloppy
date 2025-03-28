"""Convert StatsBomb event stream data to a kloppy EventDataset."""

from .deserializer import StatsBombDeserializer, StatsBombInputs

__all__ = [
    "StatsBombDeserializer",
    "StatsBombInputs",
]
