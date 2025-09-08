from typing import IO, NamedTuple


class CDFOutputs(NamedTuple):
    meta_data: IO[bytes]
    tracking_data: IO[bytes]
