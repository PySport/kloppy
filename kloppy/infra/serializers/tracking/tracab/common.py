from typing import NamedTuple, IO, Dict

from kloppy.domain import PositionType


position_types_mapping: Dict[str, PositionType] = {
    "G": PositionType.Goalkeeper,
    "D": PositionType.Defender,
    "M": PositionType.Midfielder,
    "A": PositionType.Attacker,
}


class TRACABInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]
