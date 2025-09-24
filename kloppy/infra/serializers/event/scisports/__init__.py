"""Convert SciSports event stream data to a kloppy EventDataset."""

from .deserializer import SciSportsDeserializer, SciSportsInputs

__all__ = [
    "SciSportsDeserializer",
    "SciSportsInputs",
]
