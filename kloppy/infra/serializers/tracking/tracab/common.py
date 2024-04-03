from typing import NamedTuple, IO


class TRACABInputs(NamedTuple):
    meta_data: IO[bytes]
    raw_data: IO[bytes]
